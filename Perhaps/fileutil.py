"""
doas -su mylife.root
Framework: virtual file system utilities
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import posixpath
from enum import Enum
from typing import Any, Literal, Sequence, SupportsIndex, get_origin

from Perhaps.base import *
from Perhaps.saving import save

# region Enums


class PermEnum(Enum):
    Readable = 0
    Writable = 1
    Listable = 2
    Access_Denied = 3
    Unlistable = 4
    Unwritable = 5
    Runnable = 6


# endregion

# region Consts
MUST_NEEDED_ATTRIBUTES = [
    "Permission",
    "Time",
    "Owner",
    "Contents",
]
# endregion

# region Exceptions


class DirectoryNotExists(Exception):
    pass


class FileOrDirectoryAlreadyExists(Exception):
    pass


class InvalidAttributes(Exception):
    pass


class AccessDenied(Exception):
    pass


# endregion

# region Permission helpers
def _permission_values(file_information: "FileInformation") -> list[PermEnum]:
    attribute = file_information.fileAttributes["Permission"]
    values = attribute.attrlist
    if not values:
        return []
    first = values[0]
    if isinstance(first, (list, tuple)):
        return list(first)
    return list(values)


def _visible(file_information: "FileInformation") -> bool:
    permissions = _permission_values(file_information)
    if PermEnum.Listable in permissions:
        return True
    return (
        PermEnum.Access_Denied not in permissions
        and PermEnum.Unlistable not in permissions
    )


def _require(
    file_information: "FileInformation",
    action: Literal["read", "write", "list", "execute"],
    access: Literal["system", "user", "manAI"] = "user",
) -> None:
    if access == "system":
        return
    permissions = _permission_values(file_information)
    if action == "list":
        # ``Listable`` intentionally overrides ``Access_Denied``/``Unlistable``
        # for directory listings; reading still requires Readable.
        if PermEnum.Listable in permissions:
            return
        if (
            PermEnum.Access_Denied in permissions
            or PermEnum.Unlistable in permissions
        ):
            raise AccessDenied(
                f"Directory '{file_information.fileName}' is not listable"
            )
        return
    if PermEnum.Access_Denied in permissions:
        raise AccessDenied(
            f"Access denied to file '{file_information.fileName}'"
        )
    if action == "read":
        if PermEnum.Readable not in permissions:
            raise AccessDenied(
                f"File '{file_information.fileName}' is not readable"
            )
    elif action == "write":
        if (
            PermEnum.Unwritable in permissions
            or PermEnum.Writable not in permissions
        ):
            raise AccessDenied(
                f"File '{file_information.fileName}' is not writable"
            )
    elif action == "execute":
        if PermEnum.Runnable not in permissions:
            raise AccessDenied(
                f"File '{file_information.fileName}' is not runnable"
            )


def _encode_attr_value(value: Any) -> Any:
    if isinstance(value, PermEnum):
        return {"__perm__": value.name}
    if isinstance(value, (list, tuple)):
        return [_encode_attr_value(item) for item in value]
    return value


def _decode_attr_value(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value.keys()) == {"__perm__"}:
            try:
                return PermEnum[value["__perm__"]]
            except KeyError:
                raise ValueError(
                    f"unknown permission: {value['__perm__']!r}"
                ) from None
        raise ValueError(f"invalid serialized value: {value!r}")
    if isinstance(value, list):
        return [_decode_attr_value(item) for item in value]
    return value


# endregion

# region Classes
class FileAttribute:
    def __init__(self, attrname: str, attrlist: Sequence[Any]):
        self.attrname = attrname
        self.attrlist = attrlist

    def __contains__(self, item: object) -> bool:
        for value in self.attrlist:
            if isinstance(value, (list, tuple, set)):
                if item in value:
                    return True
            elif value == item:
                return True
        return False

    def __repr__(self) -> str:
        return f"FileAttribute({self.attrname!r},{self.attrlist!r})"


class AttributeList(list):
    def __init__(self, give: Sequence[FileAttribute]):
        super().__init__(give)

    def __getitem__(self, i: str | SupportsIndex | slice, /) -> Any:
        if isinstance(i, str):
            for attr in list.__iter__(self):
                if attr.attrname == i:
                    return attr
            raise KeyError(f"Can't find attribute {i!r} in list.")
        return list.__getitem__(self, i)

    def __repr__(self) -> str:
        return f"AttributeList({list.__repr__(self)})"

    def __contains__(self, item: str | FileAttribute) -> bool:
        for attr in list.__iter__(self):
            if isinstance(item, str):
                if attr.attrname == item:
                    return True
            elif isinstance(item, FileAttribute) and attr == item:
                return True
        return False


class FileInformation:
    def __init__(self, fileName: str, fileAttributes: AttributeList):
        if not isinstance(fileName, str):
            raise TypeError("fileName must be a string")
        self.fileName = fileName
        self.fileAttributes = fileAttributes

        names = {attribute.attrname for attribute in list.__iter__(fileAttributes)}
        if any(attr not in names for attr in MUST_NEEDED_ATTRIBUTES):
            raise InvalidAttributes(
                f"File {fileName!r} doesn't have enough attributes: "
                f"{MUST_NEEDED_ATTRIBUTES}"
            )

    def __repr__(self) -> str:
        return f"FileInformation({self.fileName!r},{self.fileAttributes!r})"


class ProtectedList(list):
    """List of files that enforces file permissions for string/int access."""

    @staticmethod
    def _index_of(container: "ProtectedList", value: Any) -> int:
        if isinstance(value, bool):
            raise TypeError("bool is not a valid file index")
        if isinstance(value, int):
            return value
        if isinstance(value, FileInformation):
            for index, file in enumerate(list.__iter__(container)):
                if file is value or file.fileName == value.fileName:
                    return index
            raise ValueError(f"Can't find file {value.fileName!r} in list.")
        if isinstance(value, str):
            for index, file in enumerate(list.__iter__(container)):
                if file.fileName == value:
                    return index
            raise ValueError(f"Can't find file {value!r} in list.")
        raise TypeError("File must be a file name, a FileInformation, or an index.")

    def __contains__(self, value: object, /) -> bool:
        if isinstance(value, FileInformation):
            return any(
                file.fileName == value.fileName
                for file in list.__iter__(self)
            )
        if isinstance(value, str):
            return any(file.fileName == value for file in list.__iter__(self))
        return list.__contains__(self, value)

    def __getitem__(
        self,
        i: str | SupportsIndex | slice,
        sudo: bool = False,
        /,
    ) -> Any:
        if isinstance(i, slice):
            files = list.__getitem__(self, i)
            if sudo:
                return files
            return [file for file in files if _visible(file)]
        index = self._index_of(self, i)
        file = list.__getitem__(self, index)
        if not sudo and not _visible(file):
            raise AccessDenied(f"Access denied to file '{file.fileName}'")
        return file

    def __iter__(self, sudo: bool = False):
        for file in list.__iter__(self):
            if sudo or _visible(file):
                yield file

    def __setitem__(self, key, value, sudo: bool = False) -> None:
        index = self._index_of(self, key)
        current = list.__getitem__(self, index)
        if not sudo:
            _require(current, "write")
        list.__setitem__(self, index, value)

    def __delitem__(self, key, sudo: bool = False) -> None:
        index = self._index_of(self, key)
        current = list.__getitem__(self, index)
        if not sudo:
            _require(current, "write")
        list.__delitem__(self, index)

    def remove(self, value: FileInformation, /, sudo: bool = False) -> bool:
        index = self._index_of(self, value)
        current = list.__getitem__(self, index)
        if not sudo:
            _require(current, "write")
        list.__delitem__(self, index)
        return True

    def pop(self, index: SupportsIndex = -1, /, sudo: bool = False) -> FileInformation:
        current = list.__getitem__(self, index)
        if not sudo:
            _require(current, "write")
        return list.pop(self, index)

    def __repr__(self) -> str:
        rstr = "ProtectedList("
        for file in list.__iter__(self):
            rstr += "{" + f"{file!r}" + "}"
        rstr += ")"
        return rstr


class FileSystemPath(pathlib.PurePosixPath):
    def __init__(self, *args: str | os.PathLike[str]):
        parts: list[str] = []
        for arg in args:
            value = os.fspath(arg)
            if isinstance(value, bytes):
                value = os.fsdecode(value)
            parts.append(value)
        value = posixpath.join(*parts) if parts else "."
        if value == "~":
            value = "/home"
        elif value.startswith("~/"):
            value = "/home" + value[1:]
        super().__init__(posixpath.normpath(value))


class FileSystem:
    def __init__(
        self,
        _files: dict[str, ProtectedList],
        _directories: list[str],
    ):
        if not isinstance(_files, dict) or not isinstance(_directories, list):
            raise TypeError("FileSystem expects a dict of files and a list of directories")
        self.files = _files
        self.directories = _directories

    # ---------------------------------------------------------------- lookup
    def _entry(self, path: str, access: str = "user") -> FileInformation:
        p = FileSystemPath(path)
        parent = str(p.parent)
        if parent not in self.files:
            raise DirectoryNotExists(
                f"The directory '{parent}' is not found in file system."
            )
        try:
            return self.files[parent].__getitem__(
                p.name, access == "system"
            )
        except ValueError:
            raise FileNotFoundError(f"'{p.name}' is not exists in '{parent}'") from None

    def _require_dir_writable(self, directory: str, access: str) -> None:
        path = str(FileSystemPath(directory))
        if path == "/":
            return
        entry = self._entry(path, access=access)
        _require(entry, "write", access)  # type: ignore[arg-type]

    # ----------------------------------------------------------------- files
    def AddFile(
        self,
        parentDirectoryPath: str,
        fileInformation: FileInformation,
        access: Literal["system", "user", "manAI"] = "user",
    ) -> int:
        parentDirectoryPath = str(FileSystemPath(parentDirectoryPath))
        if parentDirectoryPath not in self.directories:
            raise DirectoryNotExists(
                f"The directory '{parentDirectoryPath}' is not found in "
                "file system registering place. Please check your code."
            )
        self._require_dir_writable(parentDirectoryPath, access)
        self.files.setdefault(parentDirectoryPath, ProtectedList([]))
        if fileInformation.fileName in self.files[parentDirectoryPath]:
            raise FileOrDirectoryAlreadyExists(
                f"There's already a file named '{fileInformation.fileName}'."
            )
        self.files[parentDirectoryPath].append(fileInformation)
        return list.__len__(self.files[parentDirectoryPath]) - 1

    def AddDirectory(
        self,
        directoryPath: str,
        permissions: Sequence[PermEnum] | None = None,
        owner: Sequence[str] | None = None,
        time: Sequence[str] | None = None,
        access: Literal["system", "user", "manAI"] = "user",
    ) -> int:
        path = FileSystemPath(directoryPath)
        directoryPath = str(path)
        if directoryPath in self.directories:
            raise FileOrDirectoryAlreadyExists(
                f"There's already a directory named '{directoryPath}'"
            )
        if permissions is None:
            permissions = [PermEnum.Listable, PermEnum.Readable, PermEnum.Writable]
        if owner is None:
            owner = ["System"]
        if time is None:
            time = [datetime.datetime.now().__str__()]

        if directoryPath == "/":
            self.directories.append(directoryPath)
            self.files[directoryPath] = ProtectedList([])
            return self.directories.index(directoryPath)

        parentPath = str(path.parent)
        if parentPath not in self.directories:
            raise DirectoryNotExists(
                f"The directory '{parentPath}' is not found in file system "
                "registering place. Please check your code."
            )
        self._require_dir_writable(parentPath, access)
        if str(path.name) in self.files.get(parentPath, ProtectedList([])):
            raise FileOrDirectoryAlreadyExists(
                f"There's already a file named '{path.name}'."
            )
        dirfile = FileInformation(
            path.name,
            AttributeList(
                [
                    FileAttribute("Permission", [list(permissions)]),
                    FileAttribute("Time", list(time)),
                    FileAttribute("Owner", list(owner)),
                    FileAttribute("Contents", ["<DIRECTORY>"]),
                    FileAttribute("Directory", ["yes"]),
                ]
            ),
        )
        self.files.setdefault(parentPath, ProtectedList([])).append(dirfile)
        self.directories.append(directoryPath)
        self.files[directoryPath] = ProtectedList([])
        return self.directories.index(directoryPath)

    def RemoveFile(
        self,
        parentDirectoryPath: str,
        file: str | FileInformation | int,
        access: Literal["system", "user", "manAI"] = "user",
    ) -> bool:
        parentDirectoryPath = str(FileSystemPath(parentDirectoryPath))
        if parentDirectoryPath not in self.directories:
            raise DirectoryNotExists(
                f"The directory '{parentDirectoryPath}' is not found in file system."
            )
        files = self.files.setdefault(parentDirectoryPath, ProtectedList([]))
        try:
            files.remove(
                files.__getitem__(file, True),
                sudo=access == "system",
            )
        except ValueError:
            return False
        return True

    def GetFileId(self, fileName: str, parentDirectoryPath: str) -> int:
        parentDirectoryPath = str(FileSystemPath(parentDirectoryPath))
        if parentDirectoryPath not in self.files:
            raise DirectoryNotExists(
                f"The directory '{parentDirectoryPath}' is not found in file system."
            )
        for index, file in enumerate(list.__iter__(self.files[parentDirectoryPath])):
            if file.fileName == fileName:
                return index
        raise FileNotFoundError(
            f"'{fileName}' is not exists in '{parentDirectoryPath}'"
        )

    def RemoveDirectory(
        self,
        path: str,
        access: Literal["system", "user", "manAI"] = "user",
    ) -> bool:
        p = FileSystemPath(path)
        directory_path = str(p)
        if directory_path not in self.directories:
            raise DirectoryNotExists(
                f"The directory '{directory_path}' is not found in file system."
            )
        if directory_path == "/":
            raise ValueError("Refusing to remove the root directory")

        _require(
            self._entry(directory_path, access=access),
            "write",
            access,  # type: ignore[arg-type]
        )
        prefix = directory_path.rstrip("/") + "/"
        subtree = [
            directory
            for directory in self.directories
            if directory == directory_path or directory.startswith(prefix)
        ]
        for directory in subtree:
            for file in list.__iter__(self.files.get(directory, [])):
                _require(file, "write", access)  # type: ignore[arg-type]

        parent = self.files.get(str(p.parent))
        if parent is not None:
            for file in list.__iter__(parent):
                if file.fileName == p.name:
                    parent.remove(file, sudo=access == "system")
                    break
        for directory in subtree:
            self.directories.remove(directory)
            self.files.pop(directory, None)
        return True

    def ReadFile(
        self,
        path: str,
        require: type = str,
        access: Literal["system", "user", "manAI"] = "user",
    ) -> str | bytes | list[str]:
        file = self._entry(path, access=access)
        _require(file, "read", access)  # type: ignore[arg-type]
        contents = list(file.fileAttributes["Contents"].attrlist)
        content = "\n".join(str(line) for line in contents)
        if require is str:
            return content
        if require is bytes:
            return content.encode()
        if require is list or get_origin(require) is list:
            return [str(line) for line in contents]
        raise ValueError(
            f"Read file only can return str, bytes, and list[str]. "
            f"{require} is not supported."
        )

    def ListDirectory(
        self,
        path: str,
        access: Literal["system", "user", "manAI"] = "user",
    ) -> ProtectedList:
        p = FileSystemPath(path)
        directory_path = str(p)
        if directory_path not in self.directories:
            raise DirectoryNotExists(
                f"The directory '{directory_path}' is not found in file system."
            )
        if directory_path != "/":
            _require(
                self._entry(directory_path, access=access),
                "list",
                access,  # type: ignore[arg-type]
            )
        files = self.files.get(directory_path, ProtectedList([]))
        if access == "system":
            return ProtectedList(list(list.__iter__(files)))
        return ProtectedList([file for file in files if _visible(file)])

    # ------------------------------------------------------------ serialization
    def to_dict(self) -> dict[str, Any]:
        files: dict[str, list[dict[str, Any]]] = {}
        for directory, protected in self.files.items():
            entries = []
            for file in list.__iter__(protected):
                attributes = {}
                for attribute in list.__iter__(file.fileAttributes):
                    attributes[attribute.attrname] = _encode_attr_value(
                        list(attribute.attrlist)
                        if isinstance(attribute.attrlist, (list, tuple))
                        else attribute.attrlist
                    )
                entries.append(
                    {"name": file.fileName, "attributes": attributes}
                )
            files[directory] = entries
        return {
            "version": 1,
            "files": files,
            "directories": list(self.directories),
        }

    def DumpToFile(self) -> str:
        """Serialize the whole file system to JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def LoadFromFile(self, dump: str) -> None:
        """Load state from JSON produced by :meth:`DumpToFile`."""
        try:
            data = json.loads(dump)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid file system dump: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("file system dump must be a JSON object")
        if data.get("version") != 1:
            raise ValueError(f"unsupported file system dump version: {data.get('version')!r}")
        raw_files = data.get("files")
        raw_dirs = data.get("directories")
        if not isinstance(raw_files, dict) or not isinstance(raw_dirs, list):
            raise ValueError("file system dump is missing files/directories")
        if not all(isinstance(directory, str) for directory in raw_dirs):
            raise ValueError("directories must be strings")

        new_files: dict[str, ProtectedList] = {}
        for directory, entries in raw_files.items():
            if not isinstance(directory, str) or not isinstance(entries, list):
                raise ValueError("invalid files section")
            protected = ProtectedList([])
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError("invalid file entry")
                name = entry.get("name")
                attributes = entry.get("attributes")
                if not isinstance(name, str) or not isinstance(attributes, dict):
                    raise ValueError("invalid file entry")
                attributes_list = AttributeList(
                    [
                        FileAttribute(
                            attr_name,
                            _decode_attr_value(attr_value),
                        )
                        for attr_name, attr_value in attributes.items()
                    ]
                )
                protected.append(FileInformation(name, attributes_list))
            new_files[directory] = protected

        self.files.clear()
        self.files.update(new_files)
        self.directories.clear()
        self.directories.extend(raw_dirs)

    def WriteFile(
        self,
        parentDirectoryPath: str,
        fileName: str,
        fileInformation: FileInformation,
        executor: Literal["system", "user", "manAI"] = "user",
    ) -> None:
        parentDirectoryPath = str(FileSystemPath(parentDirectoryPath))
        if parentDirectoryPath not in self.directories:
            raise DirectoryNotExists(
                f"The directory '{parentDirectoryPath}' is not found in file system."
            )
        files = self.files.setdefault(parentDirectoryPath, ProtectedList([]))
        if fileName in files:
            current = files.__getitem__(fileName, True)
            _require(current, "write", executor)  # type: ignore[arg-type]
            files.__setitem__(fileName, fileInformation, executor == "system")
        else:
            self.AddFile(parentDirectoryPath, fileInformation, access=executor)


# endregion

# region Files (process-wide file system)

files: dict[str, ProtectedList] = {}
directories: list[str] = []
fs = FileSystem(files, directories)


def reset_filesystem() -> FileSystem:
    """Drop all virtual files and return a fresh global file system."""
    global fs, files, directories
    files = {}
    directories = []
    fs = FileSystem(files, directories)
    return fs


def use_filesystem(file_system: FileSystem) -> FileSystem:
    """Make *file_system* the process-wide file system used by commands."""
    global fs, files, directories
    fs = file_system
    files = file_system.files
    directories = file_system.directories
    return fs


def _join_path(base: str | os.PathLike[str] | None, path: str | os.PathLike[str]) -> str:
    value = os.fspath(path)
    if value.startswith("/") or value == "~" or value.startswith("~/"):
        return value
    return posixpath.join(os.fspath(base) if base else "/", value)


def _cwd() -> str:
    # ``cd`` updates cdDirectory immediately; prefer it so the first command
    # after ``cd`` already sees the new directory (getdir runs one step later).
    for key in ("cdDirectory", "directory"):
        directory = save.get(key)
        if isinstance(directory, str) and directory:
            return directory
    return "~"


def InitBaseFileSystem() -> FileSystem:
    """Create the standard HumanOS directory tree and return the global FS."""
    global fs
    file_system = reset_filesystem()
    username, _password_hash, hostname, _salt = read_userinfo()
    if (
        not username
        or "/" in username
        or "\\" in username
        or username in (".", "..")
    ):
        raise ValueError(f"invalid username in flags/userinfo: {username!r}")

    standard_dirs = [
        "/",
        "/bin",
        "/boot",
        "/dev",
        "/etc",
        "/home",
        "/home/perhaps",
        f"/home/{username}",
        "/lib",
        "/lib64",
        "/media",
        "/mnt",
        "/opt",
        "/proc",
        "/root",
        "/run",
        "/sbin",
        "/srv",
        "/sys",
        "/tmp",
        "/usr",
        "/usr/bin",
        "/usr/include",
        "/usr/lib",
        "/usr/lib64",
        "/usr/local",
        "/usr/local/bin",
        "/usr/sbin",
        "/usr/share",
        "/var",
        "/var/cache",
        "/var/lib",
        "/var/log",
        "/var/tmp",
        "/etc/faillocks",
    ]
    for directory in dict.fromkeys(standard_dirs):
        file_system.AddDirectory(directory, access="system")

    CreateFile(
        "humansh",
        file_content=["<BINARY>"],
        file_owner=["root"],
        file_parent="/bin",
        target=file_system,
        access="system",
    )
    CreateFile(
        "hostname",
        file_content=[hostname],
        file_owner=["root"],
        file_parent="/etc",
        target=file_system,
        access="system",
    )
    CreateFile(
        "hosts",
        file_content=[
            "127.0.0.1 localhost",
            "::1 localhost ip6-localhost ip6-loopback",
        ],
        file_owner=["root"],
        file_parent="/etc",
        target=file_system,
        access="system",
    )
    CreateFile(
        "passwd",
        file_content=[
            "root:x:0:0:root:/root:/bin/humansh",
            "perhaps:x:1000:1000:Perhaps:/home/perhaps:/bin/humansh",
            f"{username}:x:1000:1000:{username}:/home/{username}:/bin/humansh",
        ],
        file_owner=["root"],
        file_parent="/etc",
        target=file_system,
        access="system",
    )
    CreateFile(
        "group",
        file_content=["root:x:0:", "perhaps:x:1000:", f"{username}:x:1000:"],
        file_owner=["root"],
        file_parent="/etc",
        target=file_system,
        access="system",
    )
    CreateFile(
        "fstab",
        file_content=[
            "/dev/sda1 / ext4 defaults 0 1",
            "tmpfs /tmp tmpfs defaults 0 0",
        ],
        file_owner=["root"],
        file_parent="/etc",
        target=file_system,
        access="system",
    )
    CreateFile(
        "resolv.conf",
        file_content=["nameserver 127.0.0.1"],
        file_owner=["root"],
        file_parent="/etc",
        target=file_system,
        access="system",
    )
    CreateFile(
        "os-release",
        file_content=[
            'NAME="HumanOS"',
            'PRETTY_NAME="HumanOS v7.2.14-nature5-5-nature"',
            "ID=humanos",
            "VERSION_ID=7.2.14",
        ],
        file_owner=["root"],
        file_parent="/etc",
        target=file_system,
        access="system",
    )
    CreateFile(
        "shadow",
        file_permission=[PermEnum.Access_Denied],
        file_content=[
            "root:*:19000:0:99999:7:::",
            "perhaps:*:19000:0:99999:7:::",
            f"{username}:*:19000:0:99999:7:::",
        ],
        file_owner=["root"],
        file_parent="/etc",
        target=file_system,
        access="system",
    )
    CreateFile(
        "messages",
        file_content=["HumanOS boot log initialized"],
        file_owner=["root"],
        file_parent="/var/log",
        target=file_system,
        access="system",
    )
    CreateFile(
        "syslog",
        file_content=["HumanOS syslog initialized"],
        file_owner=["root"],
        file_parent="/var/log",
        target=file_system,
        access="system",
    )
    return file_system


# endregion

# region Injects
@inject("getdir")
def _(directory: str) -> None:
    save.directory = directory
    if not save.gotattr("cdDirectory") or save.cdDirectory is None:
        save.cdDirectory = directory


@patcher("directory_patcher")
def _(directory: str) -> str:
    cd_directory = save.get("cdDirectory")
    return cd_directory if isinstance(cd_directory, str) and cd_directory else directory


# endregion

# region Register
@register("ls")
def _ls(args: Arguments) -> None:
    if len(args) == 0:
        path = _cwd()
    else:
        path = _join_path(_cwd(), str(args[0]))
    try:
        entries = fs.ListDirectory(str(FileSystemPath(path)))
    except DirectoryNotExists:
        print(f"ls: cannot access '{escape(str(path))}': No such directory")
        return
    except AccessDenied:
        print(f"ls: cannot access '{escape(str(path))}': Access denied")
        return
    for file_info in entries:
        color = "white"
        if "Directory" in file_info.fileAttributes:
            color = "blue"
        permissions = _permission_values(file_info)
        if PermEnum.Access_Denied in permissions:
            color = "red"
        if PermEnum.Runnable in permissions and color != "blue":
            color = "green"
        print(f"[{color}]{escape(file_info.fileName)}[/{color}]")


@register("cat")
def _cat(args: Arguments) -> None:
    if len(args) == 0:
        print("cat: missing operand")
        return
    path = str(FileSystemPath(_join_path(_cwd(), str(args[0]))))
    if path in fs.directories:
        print("cat: it's directory")
        return
    try:
        content = fs.ReadFile(path, require=str)
    except DirectoryNotExists:
        print(f"cat: cannot access '{escape(str(args[0]))}': No such directory")
        return
    except FileNotFoundError:
        print(f"cat: cannot access '{escape(str(args[0]))}': No such file")
        return
    except AccessDenied:
        print(f"cat: cannot access '{escape(str(args[0]))}': Access denied")
        return
    print(content, markup=False, emoji=False)


@register("cd")
def _cd(args: Arguments) -> None:
    if len(args) == 0:
        print("cd: missing operand")
        return
    path = str(FileSystemPath(_join_path(_cwd(), str(args[0]))))
    try:
        fs.ListDirectory(path)
    except DirectoryNotExists:
        print("cd: no such directory")
        return
    except AccessDenied:
        print("cd: access denied")
        return
    save.cdDirectory = path
    save.directory = path


# endregion

# region Help Functions
def CreateFile(
    file_name: str,
    file_permission: Sequence[PermEnum] | None = None,
    file_content: Sequence[str] | None = None,
    file_date: Sequence[str] | None = None,
    file_owner: Sequence[str] | str | None = None,
    file_parent: str = "~",
    *,
    target: FileSystem | None = None,
    access: Literal["system", "user", "manAI"] = "user",
) -> int:
    """Create a file in the virtual file system.

    :param file_owner: a string or a sequence of strings.
    :return: index of the new file in its parent directory.
    """
    if file_permission is None:
        file_permission = [PermEnum.Writable, PermEnum.Readable, PermEnum.Listable]
    if file_content is None:
        file_content = [""]
    if file_date is None:
        file_date = [datetime.datetime.now().__str__()]
    if file_owner is None:
        file_owner = ["System"]
    elif isinstance(file_owner, str):
        file_owner = [file_owner]
    file_system = target or fs
    fileinfo = FileInformation(
        file_name,
        AttributeList(
            [
                FileAttribute("Permission", [list(file_permission)]),
                FileAttribute("Time", list(file_date)),
                FileAttribute("Owner", list(file_owner)),
                FileAttribute("Contents", list(file_content)),
            ]
        ),
    )
    return file_system.AddFile(file_parent, fileinfo, access=access)


def CreateDirectory(
    directory_name: str = "",
    directory_parent: str = "~",
    full_path: str = "",
    permissions: Sequence[PermEnum] | None = None,
    date: Sequence[str] | None = None,
    owner: Sequence[str] | str | None = None,
    *,
    target: FileSystem | None = None,
    access: Literal["system", "user", "manAI"] = "user",
) -> int:
    """Create a directory.

    Pass either ``full_path`` or ``directory_name`` + ``directory_parent``.
    """
    if full_path:
        path = str(FileSystemPath(full_path))
    else:
        path = str(
            FileSystemPath(
                _join_path(directory_parent or "~", directory_name)
            )
        )
    if owner is None:
        owner = ["System"]
    elif isinstance(owner, str):
        owner = [owner]
    target_filesystem = target or fs
    return target_filesystem.AddDirectory(
        path,
        permissions,
        owner,
        date,
        access=access,
    )


def WriteFile(
    file_parent: str,
    file_source_name: str,
    file_name: str | None = None,
    file_permission: Sequence[PermEnum] | None = None,
    file_content: Sequence[str] | None = None,
    file_date: Sequence[str] | None = None,
    file_owner: Sequence[str] | str | None = None,
    is_directory: bool = False,
    access: Literal["system", "user", "manAI"] = "user",
    *,
    target: FileSystem | None = None,
) -> None:
    """Update an existing file; ``None`` arguments mean "keep unchanged"."""
    file_system = target or fs
    parent = str(FileSystemPath(file_parent))
    files = file_system.files.get(parent)
    if files is None:
        raise DirectoryNotExists(
            f"The directory '{parent}' is not found in file system."
        )
    source_file = files.__getitem__(file_source_name, True)
    attributes: dict[str, FileAttribute] = {}
    for attribute in list.__iter__(source_file.fileAttributes):
        attributes[attribute.attrname] = attribute

    if file_permission is not None:
        attributes["Permission"] = FileAttribute(
            "Permission", [list(file_permission)]
        )
    if file_content is not None:
        attributes["Contents"] = FileAttribute("Contents", list(file_content))
    if file_date is not None:
        attributes["Time"] = FileAttribute("Time", list(file_date))
    if file_owner is not None:
        if isinstance(file_owner, str):
            file_owner = [file_owner]
        attributes["Owner"] = FileAttribute("Owner", list(file_owner))
    if is_directory:
        attributes["Directory"] = FileAttribute("Directory", ["yes"])
    new_name = file_name if file_name is not None else source_file.fileName
    new_file = FileInformation(
        new_name,
        AttributeList(list(attributes.values())),
    )
    file_system.WriteFile(parent, file_source_name, new_file, access)


# endregion
