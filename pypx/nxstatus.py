# Global modules
import subprocess
import pudb
import json
import pfmisc
from pfmisc._colors import Colors
from argparse import Namespace
from typing import Any
from pathlib import Path
import os
import aiohttp
import ssl

# PYPX modules
from .base import Base

from pypx import smdb
from pypx import repack


class Status(Base):
    """
    The 'Status' class provides a similar/related interface signature
    as the other pypx classes, tailored in this case to return status
    information on a previous retrieve event.

    Like a move/retrieve module, this class expects as target information
    a SeriesInstanceUID and StudyInstanceUD.

    Unlike the other pypx classes, status events are fully serviced by
    the smdb module.
    """

    def __init__(self, arg):
        """
        Constructor.

        Largely simple/barebones constructor that calls the Base()
        and sets up the executable name.
        """

        super(Status, self).__init__(arg)
        self.dp = pfmisc.debug(verbosity=self.verbosity, within="Find", syslog=False)
        self.log = self.dp.qprint
        self.db = smdb.SMDB(Namespace(str_logDir=self.arg["dblogbasepath"]))
        self.packer = repack.Process(repack.args_impedanceMatch(Namespace(**arg)))

    def status_init(self):
        """
        Intialize the status model
        """
        d_status = {
            "status": False,
            "state": {
                "study": "NoStudyFound",
                "series": "NoSeriesFound",
                "images": "NoImagesFound",
            },
            "study": {},
            "series": {},
            "images": {
                "received": {"count": -1},
                "requested": {"count": -1},
                "packed": {"count": -1},
                "pushed": {"count": -1},
                "registered": {"count": -1},
            },
        }
        return d_status

    def requestedDICOMcount_getForSeries(self, opt: dict[str, Any]) -> int:
        requestedDICOMcount: int = 0
        d_DBtables: dict[str, Any] = self.db.seriesData_DBtablesGet(
            SeriesInstanceUID=opt["SeriesInstanceUID"]
        )
        if not d_DBtables["series-retrieve"]["exists"]:
            return 0
        recordFile: Path = Path(d_DBtables["series-retrieve"]["name"])
        content: str = recordFile.read_text()
        d_data: dict[str, Any] = json.loads(content)
        requestedDICOMcount = d_data["NumberOfSeriesRelatedInstances"]
        return int(requestedDICOMcount)

    def resolveSeriesDir(self, dir: Path) -> Path:
        fullPath: Path = dir
        fragment: str = dir.name
        if not dir.parent.exists():
            return fullPath
        ls: list[str] = os.listdir(str(dir.parent))
        hits: list[str] = [i for i in ls if fragment in i]
        if hits:
            fullPath = dir.with_name(hits[0])
        return fullPath

    def filesInDir_count(self, dir: Path) -> int:
        fileCount: int = 0
        d_CUBEs: dict[str, Any] = self.db.service_keyAccess("CUBE")
        if not d_CUBEs["status"]:
            return 0
        if self.arg["CUBE"] not in d_CUBEs["CUBE"].keys():
            return 0
        d_CUBE: dict[str, Any] = d_CUBEs["CUBE"][self.arg["CUBE"]]
        if "regFSdir" not in d_CUBE.keys():
            return 0
        targetDir: Path = Path(d_CUBE["regFSdir"] / dir)
        finalDir: Path = self.resolveSeriesDir(targetDir)
        if finalDir.exists():
            fileCount = len(os.listdir(str(finalDir)))
        return fileCount

    def CUBEinfo_get(self) -> dict[str, Any]:
        d_CUBE: dict[str, Any] = {}
        d_CUBEs: dict[str, Any] = self.db.service_keyAccess("CUBE")
        if not d_CUBEs["status"]:
            return d_CUBE
        if self.arg["CUBE"] not in d_CUBEs["CUBE"].keys():
            return d_CUBE
        d_CUBE = d_CUBEs["CUBE"][self.arg["CUBE"]]
        return d_CUBE

    async def registeredDICOMcount_getFromCUBE(self) -> int:
        # pudb.set_trace()
        d_CUBE: dict[str, Any] = self.CUBEinfo_get()
        registered: int = 0

        auth: aiohttp.BasicAuth = aiohttp.BasicAuth(
            d_CUBE["username"], d_CUBE["password"]
        )
        url: str = (
            f"{d_CUBE['url']}pacsfiles/search/?pacs_identifier=PACSDCM&SeriesInstanceUID={self.arg['SeriesInstanceUID']}"
        )

        ssl_context: ssl.SSLContext = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession(
            auth=auth, connector=aiohttp.TCPConnector(ssl=ssl_context)
        ) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data: Any = await response.json()
                    registered = data["collection"]["total"]
                else:
                    print(f"Error: {response.status}")
        return registered

    def registeredDICOMcount_getFromFS(self, d_DICOMseries: dict[str, Any]) -> int:
        registeredDICOMcount: int = 0
        d_DICOM: dict[str, Any] = {}
        d_DICOM["l_tagRaw"] = list(d_DICOMseries.keys())
        d_DICOM["dcm"] = d_DICOMseries
        d_DICOM["d_dicomSimple"] = {
            key: value["value"] for key, value in d_DICOMseries.items()
        }
        d_internalCUBEpath: dict = self.packer.packPath_resolve({"d_DICOM": d_DICOM})
        if not d_internalCUBEpath["status"]:
            return 0
        registeredDir: Path = Path(d_internalCUBEpath["packDir"])
        registeredDICOMcount = self.filesInDir_count(registeredDir)
        return registeredDICOMcount

    def status_update(
        self, requested: int, packed: int, registered: int, d_status: dict[str, Any]
    ) -> dict[str, Any]:
        d_status["status"] = False
        if requested and registered:
            d_status["status"] = True
            d_status["study"]["status"] = True
            d_status["study"]["state"] = "StudyOK"
            d_status["series"]["status"] = True
            d_status["series"]["state"] = "SeriesOK"
            d_status["state"]["images"] = "ImagesPulledAndRegisteredOK"
            d_status["study"]["seriesListInStudy"] = {}
            d_status["study"]["seriesListInStudy"]["status"] = True
        d_status["images"]["requested"]["count"] = requested
        d_status["images"]["received"]["count"] = packed
        d_status["images"]["packed"]["count"] = packed
        d_status["images"]["pushed"]["count"] = packed
        d_status["images"]["registered"]["count"] = requested
        d_status["state"]["study"] = d_status["study"]["state"]
        d_status["state"]["series"] = d_status["series"]["state"]
        return d_status

    async def run(self, opt={}) -> dict:
        # pudb.set_trace()
        d_status: dict = self.status_init()
        requested: int = self.requestedDICOMcount_getForSeries(opt)
        packed: int = self.registeredDICOMcount_getFromFS(opt["series"])
        registered: int = await self.registeredDICOMcount_getFromCUBE()
        if not registered:
            return d_status
        d_status = self.status_update(requested, packed, registered, d_status)
        d_status["study"]["seriesListInStudy"]["SeriesInstanceUID"] = opt[
            "SeriesInstanceUID"
        ]
        d_status["study"]["StudyInstanceUID"] = opt["StudyInstanceUID"]
        return d_status
