class AFException(Exception):
    pass

class AFReportNotReady(AFException):
    pass

class AFNoCompany(AFException):
    pass

class AFReportAlreadyExists(AFException):
    pass

