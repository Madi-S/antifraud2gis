class AFException(Exception):
    pass

class AFReportNotReady(AFException):
    pass

class AFNoCompany(AFException):
    pass

class AFReportAlreadyExists(AFException):
    pass

class AFNoTitle(AFException):
    """ cannot get title from reviews (probably reviews from 2gis provider) """
    pass