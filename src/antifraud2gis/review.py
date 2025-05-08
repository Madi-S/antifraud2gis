import datetime
from rich import print_json

class Review():

    _user: 'User'

    def __init__(self, data, user=None, company=None):
        # data is either from our local db or from 2gis company
        from .company import Company

        self._data = data
        

        # self.review_id = data['id']
        self.rating = data['rating']
        self.oid = data.get('oid') or data['object']['id']
        self.uid = data.get('uid') or data['user']['public_id']
        self.user_name = data.get('user_name') or data['user']['name']
        self.text = data.get('text')
        self.provider = data.get('provider')

        self._user = None
        self._company = company
        self.user_age = None

        date = data.get('date_created') or data['created']

        if 'T' in date:
            self.created = datetime.datetime.strptime(date.split('.')[0], "%Y-%m-%dT%H:%M:%S")
        else:
            self.created = datetime.datetime.strptime(date, "%Y-%m-%d")
        # self.created = datetime.datetime.strptime(data['date_created'].split('T')[0], "%Y-%m-%d")

        # age from today (grows every time)
        self.age = (datetime.datetime.now() - self.created).days

        

        if user:
            self.set_user(user)
        

        self.title, self.address = Company.resolve_oid(self.oid)

    def set_user(self, user):
        self._user = user
        if self._user.birthday():
            # set only for public profile
            self.user_age = (self.created - self._user.birthday()).days


    @property
    def created_str(self):
        return self.created.strftime("%Y-%m-%d")

    @property    
    def user(self) -> 'User': 
        if not self._user:
            from .user import User, get_user
            user = get_user(self.uid)
            self.set_user(user)

        return self._user

    @property
    def user_url(self):
        return f'https://2gis.ru/x/user/{self.uid}'


    def is_empty(self):
        if self.uid is None:
            return True

        self.user.load()
        if self.user.nreviews() <= 1:            
            return True
        
        return False

    def get_town(self) -> str: 
        if self.address is None:
            return None
        return self.address.split(',')[0].replace(u'\xa0', u' ')


    def __repr__(self):
        # print_json(data=self._data)
        from .user import User

        text_str = len(self.text) if self.text else ""

        if self.uid is None:
            user_str = "NO USER"
        else:
            u = User(self.uid)
            user_str = f"{u.name}(rev:{u.nreviews()})"

        if self.title:
            title = f"{self.title} ({self.address})"
        else:
            title = "<NO TITLE>"

        return f'Review({self.created_str} {self.provider} {self.uid} {user_str} {self.rating} > {self.oid} {title})'