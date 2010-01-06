import ctypes

DEFAULT_UUIRTDRV_LIBRARY_LOCATION = "./uuirtdrv.so"

PUUCALLBACKPROC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_void_p)
PLEARNCALLBACKPROC = ctypes.CFUNCTYPE(None, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong,  ctypes.c_void_p)

OPENEX_ATTRIBUTE_EXCLUSIVE = 0x0001

ERR_NO_DEVICE = 0x20000001
ERR_NO_RESP   = 0x20000002
ERR_NO_DLL    = 0x20000003
ERR_VERSION   = 0x20000004
ERR_IN_USE    = 0x20000005

CFG_LEDRX       = 0x0001
CFG_LEDTX       = 0x0002
CFG_LEGACYRX	= 0x0004

IRFMT_UUIRT     = 0x0000
IRFMT_PRONTO	= 0x0010

IRFMT_LEARN_FORCERAW	= 0x0100
IRFMT_LEARN_FORCESTRUC	= 0x0200
IRFMT_LEARN_FORCEFREQ	= 0x0400
IRFMT_LEARN_FREQDETECT	= 0x0800
IRFMT_LEARN_UIR		    = 0x4000
IRFMT_LEARN_DEBUG	    = 0x8000
IRFMT_TRANSMIT_DC       = 0x0080


class UUINFO (ctypes.Structure):
    """wraps uuinfo struct"""
    _fields_ = [ ("fwVersion", ctypes.c_uint),
                 ("protVersion", ctypes.c_uint),
                 ("fwDateDay", ctypes.c_ubyte),
                 ("fwDateMonth", ctypes.c_ubyte),
                 ("fwDateYear", ctypes.c_ubyte)
               ]
    
class UUGPIO (ctypes.Structure):
    """wraps uugpio struct"""
    _fields_ = [ ("irCode", ctypes.c_ubyte * 6),
                 ("action", ctypes.c_ubyte),
                 ("duration", ctypes.c_ubyte)
               ]


class UsbUirt(object):
    """Wraps the USB-UIRT C API for Python."""
    def __init__(self, library_location=DEFAULT_UUIRTDRV_LIBRARY_LOCATION):
        """Accepts a path to uuirtdrv.so - probably has to be changed a little for windows"""
        uuirtlib = ctypes.cdll.LoadLibrary(library_location)
        self.__UUIRTOpen = uuirtlib.UUIRTOpen
        self.__UUIRTOpenEx = uuirtlib.UUIRTOpenEx
        self.__UUIRTClose = uuirtlib.UUIRTClose
        self.__UUIRTGetDrvInfo = uuirtlib.UUIRTGetDrvInfo
        self.__UUIRTGetDrvVersion = uuirtlib.UUIRTGetDrvVersion
        self.__UUIRTGetUUIRTInfo = uuirtlib.UUIRTGetUUIRTInfo
        self.__UUIRTGetUUIRTConfig = uuirtlib.UUIRTGetUUIRTConfig
        self.__UUIRTSetUUIRTConfig = uuirtlib.UUIRTSetUUIRTConfig
        self.__UUIRTTransmitIR = uuirtlib.UUIRTTransmitIR
        self.__UUIRTLearnIR = uuirtlib.UUIRTLearnIR
        self.__UUIRTSetReceiveCallback = uuirtlib.UUIRTSetReceiveCallback
        self.__UUIRTGetUUIRTGPIOCfg = uuirtlib.UUIRTGetUUIRTGPIOCfg
        self.__UUIRTSetUUIRTGPIOCfg = uuirtlib.UUIRTSetUUIRTGPIOCfg
        self.__dev_handle = ctypes.c_void_p()
        self.__opened = False
        self.__receiveCallback = None
        self.__learnCallback = None
        self.__receiveUserData = None
        self.__receiveUserDataType = None
        self.__learnUserData = None
        self.__learnUserDataType = None
        
        # Python 2.6 and later - not sure what to wrap this with on earlier versions
        self.__abort = ctypes.c_bool(False)
        
    def _receiveCallback(self, codeID, userdata):
        """Translates codeID and userdata from ctypes to python objects."""
        data = None
        if (userdata):
            data = ctypes.py_object.from_address(userdata).value
        self.receiveCallback(bytes(codeID), data)
        
    def _learnCallback(self, progress, signalQuality, carrierFrequency, userdata):
        """Translates parameters from ctypes to python"""
        data = None
        if (userdata):
            data = ctypes.py_object.from_address(userdata).value
        self.learnCallback(int(progress.value), int(signalQuality.value), int(carrierFrequency.value), data)
        
    def receiveCallback(self, codeID, userdata):
        """Override this function to intercept IR code identifiers."""
        print (codeID, userdata)
        
    def learnCallback(self, progress, signalQuality, carrierFrequency, userdata):
        """Implement this function for progress reports for IR learning."""
        print (progress, signalQuality, carrierFrequency, userdata)
        
    def open(self, path, userdata=None):
        """Open the USB UIRT device.  Can throw exceptions."""
        if not self.__opened:
            self.__dev_handle = ctypes.c_void_p(self.__UUIRTOpenEx(path, 0, 0, 0))
            if self.__dev_handle:
                self.__opened = True
            else:
                raise IOError
            
            rv = self.setReceiveCallback(self._receiveCallback, userdata)
            if (rv == 0):
                raise Exception
            
    def __del__(self):
        """Close device on destroy."""
        if self.__opened:
            self.__UUIRTClose(self.__dev_handle)
            
    def close(self):
        """Close the device."""
        if self.__opened:
            # throw on error. whatcha gonna do
            rv = self.__UUIRTClose(self.__dev_handle)
            if rv == 0:
                raise Exception
            self.__opened = False

    def getDrvInfo(self):
        """Wraps UUIRTGetDrvInfo, returns Python int().  This function may be called before self.open()."""
        version = ctypes.c_uint()
        rv = self.__UUIRTGetDrvInfo(ctypes.byref(version))
        if rv == 0:
            raise Exception
        return version.value
    
    def getDrvVersion(self):
        """Wraps UUIRTGetDrvVersion, returns Python int()"""
        if not self.__opened:
            raise Exception
        version = ctypes.c_uint()
        rv = self.__UUIRTGetDrvVersion(ctypes.byref(version))
        if rv == 0:
            raise Exception
        return version.value
        
    def getUUIRTInfo(self):
        """Wraps UUIRTGetUUIRTInfo, returns usbuirt.UUINFO()."""
        if not self.__opened:
            raise Exception
        info = UUINFO()
        rv = self.__UUIRTGetUUIRTInfo(self.__dev_handle, ctypes.byref(info))
        if rv == 0:
            raise Exception
        return info
        
    def getUUIRTConfig(self):
        """Wraps UUIRTGetUUIRTConfig, returns Python int()."""
        if not self.__opened:
            raise Exception
        cfg = ctypes.c_uint32()
        puconfig = ctypes.byref(ctypes.c_uint32())
        rv = self.__UUIRTGetUUIRTConfig(self.__dev_handle, ctypes.byref(cfg))
        if rv == 0:
            raise Exception
        return cfg.value
    
    def setUUIRTConfig(self, config):
        """Wraps UUIRTSetUUIRTConfig, config is an int()."""
        if not self.__opened:
            raise Exception
        uconfig = ctypes.c_uint32(config)
        return(self.__UUIRTSetUUIRTConfig(self.__dev_handle, uconfig) == 1)
    
    def transmitIR(self, ircode, codeformat, repeatcount, inactivitywaittime):
        """Wraps UUIRTTransmitIR, ircode is a str(), other parameters are int()."""
        if not self.__opened:
            raise Exception
        code = ctypes.c_char_p(ircode)
        return (self.__UUIRTTransmitIR(self.__dev_handle, code, codeformat, repeatcount, inactivitywaittime, None, None, None) == 1)
        
    def learnIR(self, codeformat, callback, userdata, abort, param1):
        """Wraps UUIRTLearnIR, returns a list of int().
            codeformat is an int(), 
            callback is a Python ctypes function usbuirt.PLEARNCALLBACKPROC(), 
            userdata is any python object and will be sent to the callback function,
            abort is a boolean, and should be set to false - and theoretically setting it to true will interrupt the learning process
            param1 should be 0 unless there's a good reason according to the docs
            Note that changing this callback will override self.learnCallback and self._learnCallback."""
        # ircode create_string_buffer
        if not self.__opened:
            raise Exception
        buff = ctypes.create_string_buffer(4096)
        if callback:
            self.__learnCallback = PLEARNCALLBACKPROC(callback)
        
        # Python 2.6 and later.
        self.__abort = ctypes.c_bool(abort)
        self.__learnUserData = userdata
        # the type needs a reference count retained to reconstruct
        self.__learnUserDataType = ctypes.py_object(self.__learnUserData)
        rv = self.__UUIRTLearnIR(self.__dev_handle,
                                 ctypes.c_int(codeformat),
                                 ctypes.byref(buff),
                                 self.__learnCallback,
                                 ctypes.cast(ctypes.addressof(self.__learnUserDataType), ctypes.c_void_p),
                                 ctypes.byref(self.__abort),
                                 param1, None, None)
        if rv == 0:
            raise Exception
        vals = [int(x, 16) for x in buff.value.split(' ')]
        return vals
        
    def setReceiveCallback(self, callback, userdata):
        """Wrap UUIRTSetReceiveCallback, callback is of type PUUCALLBACKPROC(), userdata is any python object and will be sent to the callback.
            Note that changing this callback will override self.receiveCallback and self._receiveCallback."""
        if not self.__opened:
            raise Exception
        if callback:
            self.__receiveCallback = PUUCALLBACKPROC(callback)
        self.__receiveUserData = userdata

        # retaining a reference to this type seems necessary to reconstruct.
        # Honestly it would have been easier to keep userdata in the instance and pass None into
        # the callback, but I wanted to see I could find a way to pass it through the callback.
        self.__receiveUserDataType = ctypes.py_object(self.__receiveUserData)

        return(self.__UUIRTSetReceiveCallback(self.__dev_handle, self.__receiveCallback,
                                              ctypes.cast(ctypes.addressof(self.__receiveUserDataType), ctypes.c_void_p)))
        
    def getUUIRTGPIOCfg(self):
        """Wraps UUIRTGetUUIRTGPIOCFG. Returns a tuple of int(), int(), usbuirt.UUGPIO()."""
        if not self.__opened:
            raise Exception
        gpiostruct = UUGPIO()
        pnumslots = ctypes.c_int(0)
        pdwportpins = ctypes.c_uint32(0)
        rv = self.__UUIRTGetUUIRTGPIOCfg(self.__dev_handle, ctypes.byref(pnumslots), ctypes.byref(pdwportpins), ctypes.byref(ppiostruct))
        if rv == 0:
            raise Exception
        return (int(pnumslots.value), int(pdwportpins.value), pgpiostruct)
        
    def setUUIRTGPIOCfg(self, index, uugpio):
        """Wraps UUIRTSetUUIRTGPIOCfg.  Accepts an int() and a usbuirt.UUGPIO()."""
        if not self.__opened:
            raise Exception
        return (self.__UUIRTSetUUIRTGPIOCfg(self.__dev_handle, ctypes.c_int(index), ctypes.byref(uugpio)) == 1)
    
    
if __name__ == "__main__":
    f = UsbUirt()
    f.open("/dev/ttyUSB0")
    print "make IR signals"
    print(f.learnIR(IRFMT_PRONTO, None, None, False, 0))
    
