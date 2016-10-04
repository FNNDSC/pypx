## pre-requisites
```
dcmtk
pydicom
```

## configuration
In `xinetd` or in `launchd`, the dicom listener scripts requires the following arguments to be provided:
```
   -t: temporary directory
   -l: log directory
   -d: data directory

```
## service
In `/etc/services` add: 
```
   chris-ultron    10401/tcp   # chris ultron dicom listener
   chris-ultron    10401/udp   # chris ultron dicom listener
```

## launchd
Add `org.babymri.chris-ultron.plist` in `/Library/LaunchDaemons`.

Load: `sudo launchctl load -w org.babymri.chris-ultron.plist`

Unload: `sudo launchctl unload org.babymri.chris-ultron.plist`

Test: `nc localhost 10401` (must hang)
