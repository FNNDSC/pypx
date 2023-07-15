use anyhow::Context;
use std::path::Path;
use std::process::{Command, ExitStatus};

extern crate redis;
use redis::Commands;
use redis_derive::{FromRedisValue, ToRedisArgs};

const HELP: &str = "px-recount: conditionally runs px-repack

px-recount has the same command-line options as px-repack.
Its intended usage is as a DICOM instance handler called by storescp:

    storescp --fork -od /tmp/data -pm -sp -xcr 'px-recount --xcrdir \"#p\" --xcrfile \"#f\" --verbosity 0 --logdir /home/dicom/log --datadir /home/dicom/data --cleanup' 11113

px-recount runs px-repack if the received DICOM file given by --xcrdir
and --xcrfile is the last of its series. The number of files of a
series received so far are counted by px-repack and saved to a Redis
database.

The algorithm:

0. On input of a DICOM file
1. Read DICOM tags to get SeriesInstanceUID
2. Get NumberOfSeriesRelatedInstances and fileCounter from Redis
3. If this file is the last of its series, run px-repack.
   Else, write fileCounter+1 to Redis.


ENVIRONMENT VARIABLES

    PYPX_REDIS_URL    Redis connection URL (example: redis://redis-server.svc.local:6379)


NOTES

- It is expected that px-find writes NumberOfSeriesRelatedInstances for
  the series before px-recount runs. This is typically achieved by running
  px-find --reallyEfficient --then receive ...
- Generally, px-recount is fail-safe. It will call px-repack in the event
  of any redis-related exceptions.
";

fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "-h" || a.ends_with("-help")) {
        println!("{}", HELP);
        return anyhow::Ok(());
    }
    let (xcrdir, xcrfile) =
        get_xcr_args(&args).context("arguments --xcrdir and --xcrfile must be given.")?;

    let xcrdir = Path::new(xcrdir);
    let xcrfile = xcrdir.join(xcrfile);

    match increment_counter(&xcrfile) {
        Ok(is_last) => {
            // last DICOM file of its series, call px-repack on entire directory
            if is_last {
                repack_all(&args)?;
            }
            // else: series is not done being received, do nothing
        }
        Err(e) => {
            // something went wrong -- print error and call px-repack on just this one file
            eprintln!("{:?}", e);
            repack_one(&args)?;
            // TODO here we could do a "rescue" operation:
            // Since the series is broken anyways, we could call repack_all(args)
            // (will need to use a lock to prevent data race)
        }
    }
    anyhow::Ok(())
}

/// Call px-repack with the same arguments.
fn repack_one(args: &[String]) -> std::io::Result<ExitStatus> {
    Command::new("px-repack").args(&args[1..]).spawn()?.wait()
}

/// Call px-repack with the same arguments, but replacing the
/// arguments `--xcrfile MR_XXXXXX` with `--parseAllFilesWithSubStr ,`
fn repack_all(args: &[String]) -> std::io::Result<ExitStatus> {
    let mut prev = "";
    let mut cmd = Command::new("px-repack");
    for arg in &args[1..] {
        if arg == "--xcrfile" {
            cmd.arg("--parseAllFilesWithSubStr");
        } else if prev == "--xcrfile" {
            cmd.arg(",");
        } else {
            cmd.arg(arg);
        }
        prev = arg;
    }
    cmd.spawn()?.wait()
}

/// manual command-line argument parsing for ultra efficiency!
fn get_xcr_args(args: &[String]) -> Option<(&String, &String)> {
    let mut xcrdir = None;
    let mut xcrfile = None;
    let mut iter = args.iter();
    let mut prev = iter.next()?;

    for cur in iter {
        if prev == "--xcrdir" {
            xcrdir = Some(cur)
        } else if prev == "--xcrfile" {
            xcrfile = Some(cur)
        }
        prev = cur
    }
    xcrdir.zip(xcrfile)
}

/// Check Redis to see how many files of this series we've previously pulled.
/// If the given file is the last of its series, delete its hset from Redis
/// then return true. Otherwise, increment the counter in Redis and return false.
fn increment_counter(dcm: &Path) -> anyhow::Result<bool> {
    let series_key =
        series_key_of(dcm).with_context(|| format!("Could not read DICOM tags of {:?}", &dcm))?;

    let mut client = redis::Client::open(get_redis_url()?)?;

    let is_last = redis::transaction(&mut client, &[&series_key], |con, pipe| {
        let data: ReData = con.hgetall(&series_key)?;
        let new_count = data.fileCounter + 1;
        let status = if new_count == data.NumberOfSeriesRelatedInstances {
            pipe.del(&series_key).ignore();
            FileStatus::Last
        } else {
            pipe.hset(&series_key, "fileCounter", new_count)
                .ignore()
                .hset(&series_key, "lastUpdate", now_iso8901())
                .ignore();
            if new_count > data.NumberOfSeriesRelatedInstances {
                let error = format!(
                    "Received too many files for series. \
                    !!!SOMETHING IS VERY WRONG!!! \
                    key={} {:?}",
                    &series_key, &data
                );
                FileStatus::Exception(error)
            } else {
                FileStatus::NotLast
            }
        };
        pipe.query(con).map(|_: Option<()>| Some(status))
    })?;
    is_last.into_result()
}

/// Get the redis key name for a DICOM file.
///
/// Equivalent implementation of:
/// https://github.com/FNNDSC/pypx/blob/6ddda86cf5fdecc29a437ad5e60cf77676719af5/pypx/re.py#L10-L12
fn series_key_of(dicom_file: &Path) -> anyhow::Result<String> {
    let dcm = dicom::object::open_file(dicom_file)?;
    let series = dcm
        .element(dicom::dictionary_std::tags::SERIES_INSTANCE_UID)?
        .to_str()?;
    let key = format!("series:{series}");
    Ok(key)
}

/// Gets the value of the environment variable `PYPX_REDIS_URL`.
/// If not present, returns "redis://127.0.0.1/" by default.
fn get_redis_url() -> anyhow::Result<String> {
    match std::env::var("PYPX_REDIS_URL") {
        Ok(url) => anyhow::Ok(url),
        Err(e) => match e {
            std::env::VarError::NotPresent => anyhow::Ok("redis://127.0.0.1/".to_string()),
            std::env::VarError::NotUnicode(_) => Err(anyhow::Error::msg(
                "Value of PYPX_REDIS_URL is not unicode.",
            )),
        },
    }
}

/// Returns a ISO8601 timestamp.
fn now_iso8901() -> String {
    time::OffsetDateTime::now_utc()
        .format(&time::format_description::well_known::Iso8601::DEFAULT)
        .unwrap()
}

/// Redis hset schema for series pull progress information.
/// Matching Python implementation:
/// https://github.com/FNNDSC/pypx/blob/6ddda86cf5fdecc29a437ad5e60cf77676719af5/pypx/re.py#L15-L24
#[allow(non_snake_case)]
#[derive(Debug, FromRedisValue, ToRedisArgs, PartialEq)]
struct ReData {
    /// Number of files received by storescp, incremented by px-recount.
    fileCounter: u32,
    /// Number of DICOM files in the series, reported by px-find (findscu)
    NumberOfSeriesRelatedInstances: u32,
    /// Timestamp in ISO8901 format.
    lastUpdate: String,
}

/// The order of a received file.
#[derive(Debug, PartialEq)]
enum FileStatus {
    /// The file is the last of its series.
    Last,
    /// The file is not the last of its series and more files are yet to be recieved.
    NotLast,
    /// Unable to know whether the file is the last of its series,
    /// i.e. due to database corruption.
    Exception(String),
}

impl FileStatus {
    fn into_result(self) -> anyhow::Result<bool> {
        match self {
            FileStatus::Last => anyhow::Ok(true),
            FileStatus::NotLast => anyhow::Ok(false),
            FileStatus::Exception(e) => Err(anyhow::Error::msg(e)),
        }
    }
}
