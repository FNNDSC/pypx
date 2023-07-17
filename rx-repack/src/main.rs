use clap::Parser;
use dicom::dictionary_std::tags;
use std::path::{Path, PathBuf};

#[derive(clap::Parser)]
#[clap(
    about,
    long_about = r#"
px-repack is typically dispatched by storescp. Its purpose is to reoganize
the specified DICOM file to a path under the given data directory, putting
DICOM tag information into its new path.

The path template is:

 %PatientID-%PatientName-%PatientBirthDate
 └──%StudyDescription-%AccessionNumber-%StudyDate
    └──%_pad|5,0_SeriesNumber-%SeriesDescription
       └──%_pad|4,0_InstanceNumber-%SOPInstanceUID.dcm
"#
)]
struct Cli {
    /// Parent directory of DICOM instance
    #[clap(long)]
    xcrdir: PathBuf,
    /// File name of DICOM instance
    #[clap(long)]
    xcrfile: PathBuf,

    /// output directory
    #[clap(long)]
    datadir: PathBuf,

    /// Remove DICOM file from source location
    #[clap(long, default_value_t = false)]
    cleanup: bool,

    /// NOT IMPLEMENTED
    #[clap(long)]
    logdir: Option<PathBuf>,

    /// Deprecated option
    #[clap(long)]
    verbosity: Option<u8>,
}

fn main() -> anyhow::Result<()> {
    let args: Cli = Cli::parse();
    let input_file = args.xcrdir.join(&args.xcrfile);
    let (series_dir, out_fname) = repacked_path_of(&input_file, &args.datadir)?;
    let output_file = series_dir.join(out_fname);

    std::fs::create_dir_all(series_dir)?;
    if args.cleanup {
        std::fs::rename(input_file, output_file)?;
    } else {
        std::fs::copy(input_file, output_file)?;
    }
    anyhow::Ok(())
}

fn repacked_path_of<P: AsRef<Path>>(
    dicom_file: P,
    data_dir: P,
) -> anyhow::Result<(PathBuf, String)> {
    let dcm = dicom::object::open_file(dicom_file)?;
    let dicom_info = DicomInfo::try_from(dcm)?;
    let (pack_dir, fname) = dicom_info.to_path_parts();
    Ok((data_dir.as_ref().join(pack_dir), fname))
}

#[allow(non_snake_case)]
struct DicomInfo {
    PatientID: String,
    PatientName: String,
    PatientBirthDate: String,
    StudyDescription: String,
    AccessionNumber: String,
    StudyDate: String,
    SeriesNumber: u32,
    SeriesDescription: String,
    InstanceNumber: u32,
    SOPInstanceUID: String,
}

impl TryFrom<dicom::object::DefaultDicomObject> for DicomInfo {
    type Error = dicom::object::Error;

    fn try_from(dcm: dicom::object::DefaultDicomObject) -> Result<Self, Self::Error> {
        let info = Self {
            PatientID: dcm.element(tags::PATIENT_ID)?.to_str().unwrap().to_string(),
            PatientName: dcm
                .element(tags::PATIENT_NAME)?
                .to_str()
                .unwrap()
                .to_string(),
            PatientBirthDate: dcm
                .element(tags::PATIENT_BIRTH_DATE)?
                .to_str()
                .unwrap()
                .to_string(),
            StudyDescription: dcm
                .element(tags::STUDY_DESCRIPTION)?
                .to_str()
                .unwrap()
                .to_string(),
            AccessionNumber: dcm
                .element(tags::ACCESSION_NUMBER)?
                .to_str()
                .unwrap()
                .to_string(),
            StudyDate: dcm.element(tags::STUDY_DATE)?.to_str().unwrap().to_string(),
            SeriesNumber: dcm
                .element(tags::SERIES_NUMBER)?
                .to_str()
                .unwrap()
                .parse()
                .unwrap(),
            SeriesDescription: dcm
                .element(tags::SERIES_DESCRIPTION)?
                .to_str()
                .unwrap()
                .to_string(),
            InstanceNumber: dcm
                .element(tags::INSTANCE_NUMBER)?
                .to_str()
                .unwrap()
                .parse()
                .unwrap(),
            SOPInstanceUID: dcm
                .element(tags::SOP_INSTANCE_UID)?
                .to_str()
                .unwrap()
                .to_string(),
        };
        Ok(info)
    }
}

impl DicomInfo {
    /// Produce the destination directory and file name for the DICOM file.
    /// Equivalent Python implementation is `pypx.repack.Process.packPath_resolve`
    /// https://github.com/FNNDSC/pypx/blob/d4791598f65b257cbf6b17d6b5b05db777844db4/pypx/repack.py#L412-L459
    fn to_path_parts(&self) -> (PathBuf, String) {
        let root_dir = format!(
            "{}-{}-{}",
            &self.PatientID, &self.PatientName, &self.PatientBirthDate
        );
        let study_dir = format!(
            "{}-{}-{}",
            &self.StudyDescription, &self.AccessionNumber, &self.StudyDate
        );
        let series_dir = format!("{:0>5}-{}", &self.SeriesNumber, &self.SeriesDescription);
        let image_file = format!("{:0>4}-{}", &self.InstanceNumber, &self.SOPInstanceUID);
        (
            PathBuf::from(root_dir).join(study_dir).join(series_dir),
            image_file,
        )
    }
}
