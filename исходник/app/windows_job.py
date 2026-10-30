"""Windows Job Object: kill descendants when coordinator/job handle is closed."""
import os

def assign(pid):
 if os.name!='nt':return None
 import ctypes
 from ctypes import wintypes as w
 class BASIC(ctypes.Structure):
  _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',w.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',w.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
 class IO(ctypes.Structure):
  _fields_=[(n,ctypes.c_ulonglong) for n in ['ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount']]
 class EXTENDED(ctypes.Structure):
  _fields_=[('BasicLimitInformation',BASIC),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 k.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];k.CreateJobObjectW.restype=w.HANDLE
 k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD];k.SetInformationJobObject.restype=w.BOOL
 k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
 k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];k.AssignProcessToJobObject.restype=w.BOOL
 k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
 handle=k.CreateJobObjectW(None,None)
 if not handle:raise ctypes.WinError(ctypes.get_last_error())
 info=EXTENDED();info.BasicLimitInformation.LimitFlags=0x2000
 if not k.SetInformationJobObject(handle,9,ctypes.byref(info),ctypes.sizeof(info)):
  code=ctypes.get_last_error();k.CloseHandle(handle);raise ctypes.WinError(code)
 process=k.OpenProcess(0x0100|0x0001,False,pid)
 if not process:code=ctypes.get_last_error();k.CloseHandle(handle);raise ctypes.WinError(code)
 try:
  if not k.AssignProcessToJobObject(handle,process):
   code=ctypes.get_last_error();k.CloseHandle(handle);raise ctypes.WinError(code)
 finally:k.CloseHandle(process)
 return handle

def close(handle):
 if handle is None:return
 import ctypes
 from ctypes import wintypes
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.CloseHandle.argtypes=[wintypes.HANDLE];k.CloseHandle(handle)
