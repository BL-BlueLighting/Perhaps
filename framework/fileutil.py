"""
doas -su mylife.root
Framework: File System (virtual) utils
"""
import datetime
import os
import pathlib
import posixpath
from enum import Enum
from typing import Any, Sequence, SupportsIndex, get_origin

from framework import *

#region Enums
class PermEnum(Enum):
    Readable = 0
    Writable = 1
    Listable = 2
    Access_Denied = 3
    Unlistable = 4
    Unwritable = 5
    Runnable = 6
#endregion

#region Consts
MUST_NEEDED_ATTRIBUTES = [
    "Permission",
    "Time",
    "Owner",
    "Contents"
]
#endregion

#region Exceptions
class DirectoryNotExists(Exception):
    pass

class FileOrDirectoryAlreadyExists(Exception):
    pass

class InvalidAttributes(Exception):
    pass

class AccessDenied(Exception):
    pass
#endregion

#region Classes

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
        parts: list[str] = []
        for attr in self.attrlist:
            if isinstance(attr, (list, tuple)):
                parts.append("".join(f"{item}<" for item in attr))
            else:
                parts.append(str(attr))
        return f"{self.attrname}:" + ";".join(parts) + (";" if parts else "")

class AttributeList(list):
    def __init__(self, give: Sequence[FileAttribute]):
        super().__init__(give)

    def __getitem__(self, i: str | SupportsIndex | slice, /) -> Any:
        if isinstance(i, str):
            if i.lstrip("-").isdigit():
                return list.__getitem__(self, int(i))
            for attr in list.__iter__(self):
                if attr.attrname == i:
                    return attr
            raise ValueError("Can't find attribute in list.")
        return list.__getitem__(self, i)

    def __repr__(self) -> str:
        rstr = f"Attributes("
        for attr in list.__iter__(self):
            rstr += f"[{attr!r}]"
        rstr += ")"
        return rstr

    def __contains__(self, item: str | FileAttribute) -> bool:
        for attr in list.__iter__(self):
            if type(item) == str:
                if attr.attrname == item:
                    return True
            if type(item) == FileAttribute:
                if attr == item:
                    return True
        return False

class FileInformation:
    def __init__(self, fileName: str, fileAttributes: AttributeList):
        self.fileName = fileName
        self.fileAttributes = fileAttributes

        # must need attributes
        names = {attribute.attrname for attribute in fileAttributes}
        if any(attr not in names for attr in MUST_NEEDED_ATTRIBUTES):
            raise InvalidAttributes("File don't have enough attributes.")

    def __repr__(self) -> str:
        return f"FileInformation({self.fileName},{self.fileAttributes!r})"

class ProtectedList(list):
    def __contains__(self, value: object, /) -> bool:
        if isinstance(value, FileInformation):
            return any(file.fileName == value.fileName for file in list.__iter__(self))
        return list.__contains__(self, value)

    def remove(self, value: FileInformation, /) -> bool:
        permissions = value.fileAttributes["Permission"]
        if PermEnum.Access_Denied in permissions:
            raise AccessDenied(f"Access denied to file '{value.fileName}'")
        if PermEnum.Unwritable in permissions:
            return False
        list.remove(self, value)
        return True

    def pop(self, index: SupportsIndex = -1, /) -> bool:
        return self.remove(list.__getitem__(self, index))

    def __getitem__(self, i: str | SupportsIndex | slice, sudo: bool = False, /) -> Any:
        if isinstance(i, str):
            if i.lstrip("-").isdigit():
                return list.__getitem__(self, int(i))
            for file in list.__iter__(self):
                if file.fileName == i:
                    permissions = file.fileAttributes["Permission"]
                    if (PermEnum.Access_Denied in permissions or PermEnum.Unlistable in permissions) and not sudo:
                        raise AccessDenied(f"Access denied to file '{file.fileName}'")
                    return file
            raise ValueError("Can't find file in list.")
        return list.__getitem__(self, i)

    def __iter__(self, sudo: bool = False):
        def visible(file: FileInformation) -> bool:
            permissions = file.fileAttributes["Permission"]
            return (((PermEnum.Access_Denied not in permissions) and (PermEnum.Unlistable not in permissions)) or (PermEnum.Listable in permissions)) and not sudo

        return iter([file for file in list.__iter__(self) if visible(file)])

    def __repr__(self) -> str:
        rstr = "ProtectedList("
        for fi in list.__iter__(self):
            rstr += "{" + f"{fi!r}" + "}"
        rstr += ")"
        return rstr

    def __setitem__(self, key, value):
        permCheck = self.__getitem__(key)
        return list.__setitem__(self, key, value)

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
    def __init__(self, _files: dict[str, ProtectedList], _directories: list[str]):
        """
        Create new FileSystem.

        :param _files: Files.
        :param _directories: Directories.
        """
        # oh shit bro, why did i write this comment?
        self.files = _files
        self.directories = _directories

    def AddFile(self, parentDirectoryPath: str, fileInformation: FileInformation) -> int:
        """
        Add file into FileSystem's files list.

        :param parentDirectoryPath: This file will storage at?
        :param fileInformation: File information.
        :return int: index
        """
        parentDirectoryPath = str(FileSystemPath(parentDirectoryPath))
        if parentDirectoryPath not in self.directories:
            raise DirectoryNotExists(f"The directory '{parentDirectoryPath}' is not found in file system registering place. Please check your code.")

        self.files.setdefault(parentDirectoryPath, ProtectedList([]))

        if fileInformation in self.files[parentDirectoryPath]:
            raise FileOrDirectoryAlreadyExists(f"There's already a file named '{fileInformation.fileName}'.")

        self.files[parentDirectoryPath].append(fileInformation)
        return self.files[parentDirectoryPath].index(fileInformation)

    def AddDirectory(self,
                     directoryPath: str,
                     permissions: Sequence[PermEnum] | None = None,
                     owner: Sequence[str] | None = None,
                     time: Sequence[str] | None = None
        ) -> int:
        """
        Add new empty directory into FileSystem's directory list.

        :param directoryPath: where is this directory.
        :param permissions: permission list.
        :return int: directory's index
        """
        path = FileSystemPath(directoryPath)
        directoryPath = str(path)
        if directoryPath in self.directories:
            raise FileOrDirectoryAlreadyExists(f"There's already a directory named '{directoryPath}'")

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
            raise DirectoryNotExists(f"The directory '{parentPath}' is not found in file system registering place. Please check your code.")

        dirfile = FileInformation(
            path.name,
            AttributeList(
                [
                    FileAttribute("Permission", [list(permissions)]),
                    FileAttribute("Time", time),
                    FileAttribute("Owner", owner),
                    FileAttribute("Contents", ["<DIRECTORY>"]),
                    FileAttribute("Directory", ["yes"])
                ]
            )
        )
        self.AddFile(parentPath, dirfile)
        self.directories.append(directoryPath)
        self.files[directoryPath] = ProtectedList([])
        return self.directories.index(directoryPath)

    def RemoveFile(self, parentDirectoryPath: str, file: str | FileInformation | int) -> bool:
        """
        Remove a File from {parentDirectoryPath}

        :param parentDirectoryPath: Which dir.
        :param file: fileName or fileInformation or index.
        """
        parentDirectoryPath = str(FileSystemPath(parentDirectoryPath))
        if parentDirectoryPath not in self.directories:
            raise DirectoryNotExists(f"The directory '{parentDirectoryPath}' is not found in file system.")
        if isinstance(file, str):
            for _file in list.__iter__(self.files[parentDirectoryPath]):
                if _file.fileName == file:
                    return self.files[parentDirectoryPath].remove(_file)
            return False
        elif isinstance(file, FileInformation):
            return self.files[parentDirectoryPath].remove(file)
        elif isinstance(file, int) and not isinstance(file, bool):
            return self.files[parentDirectoryPath].pop(file)
        else:
            raise TypeError("File must be a file name, a FileInformation, or an index.")

    def GetFileId(self, fileName: str, parentDirectoryPath: str) -> int:
        """
        Get file's index in list by file name.
        """
        parentDirectoryPath = str(FileSystemPath(parentDirectoryPath))
        if parentDirectoryPath not in self.files:
            raise DirectoryNotExists(f"The directory '{parentDirectoryPath}' is not found in file system.")
        for index, _file in enumerate(list.__iter__(self.files[parentDirectoryPath])):
            if _file.fileName == fileName:
                return index
        raise FileNotFoundError(f"'{fileName}' is not exists in '{parentDirectoryPath}'")

    def RemoveDirectory(self, path: str) -> bool:
        """
        Remove all files in directory and its self

        :param path: where's this dir.
        """
        p = FileSystemPath(path)
        path = str(p)
        if path not in self.directories:
            raise DirectoryNotExists(f"The directory '{path}' is not found in file system.")
        if path != "/":
            parent = self.files.get(str(p.parent))
            if parent is not None:
                for _file in list.__iter__(parent):
                    if _file.fileName == p.name:
                        if not parent.remove(_file):
                            return False
                        break
        prefix = path.rstrip("/") + "/"
        for directory in [d for d in self.directories if d == path or d.startswith(prefix)]:
            self.directories.remove(directory)
            self.files.pop(directory, None)
        return True

    def ReadFile(self, path: str, require: type = str, access: LiteralString["system", "user", "manAI"] = "user") -> str | bytes | list[str]:
        """
        Read file.
        """
        p = FileSystemPath(path)
        # bro i lazy to make a new system for path. IT'S ENOUGH!!!
        pardir = str(p.parent)
        if pardir not in self.files:
            raise DirectoryNotExists(f"The directory '{pardir}' is not found in file system.")

        file = self.files[pardir][self.GetFileId(p.name, pardir)]
        permissions = file.fileAttributes["Permission"]
        if (PermEnum.Access_Denied in permissions or PermEnum.Readable not in permissions) and access != "system":
            raise AccessDenied(f"Access denied to file '{p.name}'")

        contents = list(file.fileAttributes["Contents"].attrlist)
        content = "\n".join(str(line) for line in contents)
        if require is str:
            return content
        elif require is bytes:
            return content.encode()
        elif require is list or get_origin(require) is list:
            return [str(line) for line in contents]
        else:
            raise ValueError(f"Read file only can return str, bytes, and list[str]. {require} is not supported.")

    def ListDirectory(self, path: str) -> list[FileInformation]:
        """
        List directory.
        """
        p = FileSystemPath(path)
        directoryPath = str(p)
        if directoryPath not in self.directories:
            raise DirectoryNotExists(f"The directory '{directoryPath}' is not found in file system.")
        if directoryPath != "/" and str(p.parent) in self.files:
            try:
                self.files[str(p.parent)][p.name]
            except ValueError:
                pass
        return self.files.setdefault(directoryPath, ProtectedList([]))

    def DumpToFile(self) -> str:
        """
        Dump all file system to string.
        """
        rstr = "FileSystem(files={"
        for dirpath, files in self.files.items():
            rstr += "{" + dirpath + ":" + files.__repr__() + "}"
        rstr += ";}directories=["
        for d in self.directories:
            rstr += d + ";"
        rstr += "];)"
        return rstr

    def _parse_value(self, token: str) -> str | int | PermEnum:
        if token.lstrip("-").isdigit():
            return int(token)
        prefix = "PermEnum."
        if token.startswith(prefix) and token[len(prefix):] in PermEnum.__members__:
            return PermEnum[token[len(prefix):]]
        return token

    def _parse_attribute(self, astr: str) -> FileAttribute:
        """Parse one FileAttribute repr like 'name:a;b;c<d<;'."""
        name, _, rest = astr.partition(":")
        attrlist: list[Any] = []
        for segment in rest.split(";"):
            if segment == "":
                continue
            if segment.endswith("<"):
                attrlist.append([self._parse_value(token) for token in segment[:-1].split("<") if token != ""])
            else:
                attrlist.append(self._parse_value(segment))
        return FileAttribute(name, attrlist)

    def _parse_attributes(self, astr: str) -> AttributeList:
        """Parse 'Attributes([...][...])'."""
        body = astr[len("Attributes("):-1]
        attrs: list[FileAttribute] = []
        i = 0
        while i < len(body):
            if body[i] == "[":
                j = body.index("]", i)
                attrs.append(self._parse_attribute(body[i + 1:j]))
                i = j + 1
            else:
                i += 1
        return AttributeList(attrs)

    def _parse_file_information(self, fstr: str) -> FileInformation:
        """Parse 'FileInformation(fileName,Attributes(...))'."""
        body = fstr[len("FileInformation("):-1]
        # split at first comma
        name, _, attrs_part = body.partition(",")
        return FileInformation(name, self._parse_attributes(attrs_part))

    def _parse_protected_list(self, pstr: str) -> ProtectedList:
        """Parse 'ProtectedList({...}{...})'."""
        body = pstr[len("ProtectedList("):-1]
        pl = ProtectedList([])
        i = 0
        while i < len(body):
            if body[i] == "{":
                depth = 0
                j = i
                while j < len(body):
                    if body[j] == "{":
                        depth += 1
                    elif body[j] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                pl.append(self._parse_file_information(body[i + 1:j]))
                i = j + 1
            else:
                i += 1
        return pl

    def LoadFromFile(self, dump: str) -> None:
        """
        Load file system state from a string produced by DumpToFile.

        :param dump: the serialized string.
        """
        # strip outer 'FileSystem(' and ')'
        if not (dump.startswith("FileSystem(") and dump.endswith(")")):
            raise ValueError("Not a valid FileSystem dump.")
        body = dump[len("FileSystem("):-1]

        # split 'files={...};directories=[...];'
        files_tag = "files={"
        dirs_tag = ";}directories=["
        fi = body.index(files_tag) + len(files_tag)
        di = body.index(dirs_tag)

        files_body = body[fi:di]
        dirs_part = body[di + len(dirs_tag):]
        closing = dirs_part.rfind("]")
        if closing != -1:
            dirs_part = dirs_part[:closing]

        # parse files: sequence of {dirpath:ProtectedList(...)}
        new_files: dict[str, ProtectedList] = {}
        i = 0
        while i < len(files_body):
            if files_body[i] != "{":
                i += 1
                continue
            # find matching '}' accounting for nested braces
            depth = 0
            j = i
            while j < len(files_body):
                if files_body[j] == "{":
                    depth += 1
                elif files_body[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            inner = files_body[i + 1:j]
            dirpath, _, pl_part = inner.partition(":")
            new_files[dirpath] = self._parse_protected_list(pl_part)
            i = j + 1

        # parse directories: 'dir1;dir2;...'
        new_dirs = [d for d in dirs_part.split(";") if d != ""]

        self.files.clear()
        self.files.update(new_files)
        self.directories.clear()
        self.directories.extend(new_dirs)

    def WriteFile(self,
                  parentDirectoryPath: str,
                  fileName: str,
                  fileInformation: FileInformation,
                  executor: LiteralString["system", "user", "manAI"] = "user"):
        """
        Write information to file.

        :param parentDirectoryPath: Parent directory full path.
        :param fileName: file's name.
        :param fileInformation: replace fileInformation.
        :param executor: who wants to execute. executor = user/system/manAI.
        """
        sourceFile: FileInformation = self.files[parentDirectoryPath].__getitem__(fileName, True)
        if ((PermEnum.Access_Denied in sourceFile.fileAttributes) or (PermEnum.Unwritable in sourceFile.fileAttributes)) and (not executor == "system") and (not rdflag("userinfo").split("\n")[0] == sourceFile.fileAttributes.__getitem__("Owner")):
            raise AccessDenied(f"You haven't access to write '{fileName}'.")

        self.files[parentDirectoryPath][fileName] = fileInformation

#endregion

#region Files
files: dict[
    str,
    ProtectedList
] = {}

"""
files:
dict [
    directoryPath: str,
    files: list[
        filesInformation: FileInformation[
            fileName: str,
            fileAttributes: list[FileAttribute] (
                fileAttribute: FileAttribute (
                    attributeName: str,
                    attributeList: list[str | int]
                )
            )
        ]
    ]
]
(do not add \\n at end of contentLines.)
"""

directories: list[str] = []

def _join_path(base: str | None, path: str) -> str:
    if path.startswith("/") or path == "~" or path.startswith("~/"):
        return path
    return posixpath.join(base or "/", path)

fs = FileSystem(files, directories)

def InitBaseFileSystem():
    fs = FileSystem(files, directories)

    userinfo = rdflag("userinfo").split("\n")
    user = userinfo[0]
    pwdhash = userinfo[1]
    hostname = userinfo[2]
    hashsalt = userinfo[3]

    for _directory in [
        "/",
        "/bin",
        "/boot",
        "/dev",
        "/etc",
        "/home",
        "/home/perhaps",
        "/home/" + user,
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
        "/etc/faillocks/"
    ]:
        fs.AddDirectory(_directory)
    #endregion

    CreateFile("humansh", file_content=["<BINARY>"], file_owner=["root"], file_parent="/bin")
    CreateFile("hostname", file_content=[hostname], file_owner=["root"], file_parent="/etc")
    CreateFile(
        "hosts",
        file_content=[
            "127.0.0.1 localhost",
            "::1 localhost ip6-localhost ip6-loopback",
        ],
        file_owner=["root"],
        file_parent="/etc",
    )
    CreateFile(
        "passwd",
        file_content=[
            "root:x:0:0:root:/root:/bin/humansh",
            "perhaps:x:1000:1000:Perhaps:/home/perhaps:/bin/humansh",
            f"{user}:x:1000:1000:{user}:/home/{user}:/bin/humansh"
        ],
        file_owner=["root"],
        file_parent="/etc",
    )
    CreateFile(
        "group",
        file_content=[
            "root:x:0:",
            "perhaps:x:1000:",
            f"{user}:x:1000:"
        ],
        file_owner=["root"],
        file_parent="/etc",
    )
    CreateFile(
        "fstab",
        file_content=[
            "/dev/sda1 / ext4 defaults 0 1",
            "tmpfs /tmp tmpfs defaults 0 0",
        ],
        file_owner=["root"],
        file_parent="/etc",
    )
    CreateFile("resolv.conf", file_content=["nameserver 127.0.0.1"], file_owner=["root"], file_parent="/etc")
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
    )
    CreateFile(
        "shadow",
        file_permission=[PermEnum.Access_Denied],
        file_content=[
            "root:*:19000:0:99999:7:::",
            "perhaps:*:19000:0:99999:7:::",
            f"{user}:*:19000:0:99999:7:::"
        ],
        file_owner=["root"],
        file_parent="/etc",
    )
    CreateFile("messages", file_content=["HumanOS boot log initialized"], file_owner=["root"], file_parent="/var/log")
    CreateFile("syslog", file_content=["HumanOS syslog initialized"], file_owner=["root"], file_parent="/var/log")

    return fs

#region Injects

@inject("getdir")
def _(args: str):
    try:
        tmp = save.directory
    except:
        return "~"

    save.directory = args
    if save.cdDirectory is None:
        save.cdDirectory = args

@inject("directory_patcher")
def _(args: str):
    try:
        tmp = save.cdDirectory
    except:
        return "~"

    if save.cdDirectory is None:
        return args
    return save.cdDirectory

#endregion

#region Register
@register("ls")
def _ls(args: Arguments):
    if len(args) == 0:
        path = save.directory or "~"
    else:
        path = _join_path(save.directory, str(args[0]))

    try:
        files_in_dir = fs.ListDirectory(str(path))
        for file_info in files_in_dir:
            fileColor = "white"
            if "Directory" in file_info.fileAttributes:
                fileColor = "blue"
            if PermEnum.Access_Denied in file_info.fileAttributes["Permission"]:
                fileColor = "red"
            if PermEnum.Runnable in file_info.fileAttributes["Permission"] and fileColor != "blue":
                fileColor = "green"  # bro you make a directory runnable is hyw?
            print(f"[{fileColor}]{file_info.fileName}[/{fileColor}]")
    except DirectoryNotExists:
        print(f"ls: cannot access '{path}': No such directory")
    except AccessDenied:
        print(f"ls: cannot access '{path}': Access denied")

@register("cat")
def _cat(args: Arguments):
    if len(args) == 0:
        print("cat: missing operand")
        return
    path = str(FileSystemPath(_join_path(save.directory, str(args[0]))))
    if path in fs.directories:
        print("cat: it's directory")
        return
    try:
        content = fs.ReadFile(path, require=str)
        if content == "<DIRECTORY>":
            print("cat: it's directory")
            return
        print(content, markup=False, emoji=False)
    except DirectoryNotExists:
        print(f"cat: cannot access '{args[0]}': No such directory")
    except FileNotFoundError:
        print(f"cat: cannot access '{args[0]}': No such file")
    except AccessDenied:
        print(f"cat: cannot access '{args[0]}': Access denied")

@register("cd")
def _cd(args: Arguments):
    if len(args) == 0:
        print("cd: missing operand")
        return

    path = str(FileSystemPath(_join_path(save.directory, str(args[0]))))
    try:
        fs.ListDirectory(path)
    except DirectoryNotExists:
        print("cd: no such directory")
        return
    except AccessDenied:
        print("cd: access denied")
        return

    save.cdDirectory = path
    return

#endregion

#region Help Functions
def CreateFile(
        file_name: str,
        file_permission: Sequence[PermEnum] | None = None,
        file_content: Sequence[str] | None = None,
        file_date: Sequence[str] | None = None,
        file_owner: Sequence[str] | None = None,
        file_parent: str = "~"
) -> int:
    """
    Create file.

    :param file_name: File's name.
    :param file_permission: Permissions. Using PermEnum, or direct use int.
    :param file_content: File content lines. No \\n.
    :param file_date: File create date. STRING!!!!
    :param file_owner: Who creates this file or who own it.
    :param file_parent: File's parent directory, REMEMBER REPLACE TO save.directory!!!
    :return int: file index id in file_parent.
    """
    if file_permission is None:
        file_permission = [PermEnum.Writable, PermEnum.Readable, PermEnum.Listable]
    if file_content is None:
        file_content = [""]
    if file_date is None:
        file_date = [datetime.datetime.now().__str__()]
    if file_owner is None:
        file_owner = ["System"]
    fileinfo = FileInformation(
        file_name,
        AttributeList(
            [
                FileAttribute("Permission", [list(file_permission)]),
                FileAttribute("Time", list(file_date)),
                FileAttribute("Owner", list(file_owner)),
                FileAttribute("Contents", list(file_content))
            ]
        )
    )
    return fs.AddFile(file_parent, fileinfo)

def CreateDirectory(
        directory_name: str,
        directory_parent: str,
        full_path: str = "",
        permissions: Sequence[PermEnum] | None = None,
        date: Sequence[str] | None = None,
        owner: Sequence[str] | None = None,
):
    """
    Create new Directory.

    :param directory_name: Directory's name.
    :param directory_parent: Directory's parent.
    :param full_path: If you enter this argument, name and parent will be automatic
    get name and parent, you can do not write 2 args above.
    :param permissions: Directory permissions. PermEnum plz.
    :param date: String date.
    :param owner: String owner.
    """
    if permissions is None:
        permissions = [PermEnum.Writable, PermEnum.Readable, PermEnum.Listable]
    if date is None:
        date = [datetime.datetime.now().__str__()]
    if owner is None:
        owner = ["System"]

    if not full_path is None:
        # analyze name and parent from full path.
        p = FileSystemPath(full_path)
        directory_name = p.name
        directory_parent = p.parent

    fs.AddDirectory(_join_path(directory_name, directory_parent), permissions)

def WriteFile(
        file_parent: str,
        file_source_name: str,
        file_name: str | None = None,
        file_permission: Sequence[PermEnum] | None = None,
        file_content: Sequence[str] | None = None,
        file_date: Sequence[str] | None = None,
        file_owner: Sequence[str] | None = None,
        is_directory: bool = False,
        access: LiteralString["system", "user", "manAI"] = "user"
) -> None:
    """
    Write file / directory.

    :param file_parent: File's parent (unchangable)
    :param file_source_name: File's source name.
    :param file_name: File's new name.
    :param file_permission: New permissions. Using PermEnum, or direct use int.
    :param file_content: New file content lines. No \\n.
    :param file_date: New file create date. STRING!!!!
    :param file_owner: Who creates this file or who own it.
    :param access: Access permission.
    :return None: nothing

    All arguments leave None / Blank means unchange.
    """
    sourceFile: FileInformation = fs.files[file_parent].__getitem__(file_source_name, True)
    extend_attr = FileAttribute("", "")

    if file_permission is None:
        file_permission = sourceFile.fileAttributes["Permission"]
    if file_content is None:
        file_content = sourceFile.fileAttributes["Contents"]
    if file_date is None:
        file_date = sourceFile.fileAttributes["Time"]
    if file_owner is None:
        file_owner = sourceFile.fileAttributes["Owner"]
    if file_name is None:
        file_name = sourceFile.fileName
    if is_directory:
        extend_attr = FileAttribute("Directory", ["yes"])

    newFile = FileInformation(file_name, AttributeList(
        [
            file_permission,
            file_content,
            file_date,
            file_owner,
            extend_attr if extend_attr != FileAttribute("", "") else None
        ]
    ))
    return fs.WriteFile(file_parent, file_source_name, newFile, access)
#endregion

# IT'S WHAT MOTHER FUCKING CODES I WROTE I WASTED MANY HOURS TO WRITE THIS SHIT
# FUCK U MY BRAIN