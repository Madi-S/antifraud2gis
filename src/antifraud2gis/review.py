import datetime
from rich import print_json

class Review():
    def __init__(self, data, user=None, company=None):
        self._data = data
        self.review_id = data['id']
        self.rating = data['rating']
        self.oid = data['object']['id']
        self.uid = data['user']['public_id']
        self.user_name = data['user']['name']
        self.text = data.get('text')        
        self.nphotos = len(data['photos'])

        self._user = None
        self._company = company
        self.user_age = None

        self.created = datetime.datetime.strptime(data['date_created'].split('T')[0], "%Y-%m-%d")

        # age from today (grows every time)
        self.age = (datetime.datetime.now() - self.created).days

        

        if user:
            self.set_user(user)
        

        if self._company:
            self.title = self._company.title
            self.address = self._company.address

        else:
            try:
                self.title = data['object']['name']
            except KeyError:
                self.title = None

            try:
                self.address = data['object']['address']
            except KeyError:
                self.address = None

    def set_user(self, user):
        self._user = user
        if self._user.birthday():
            # set only for public profile
            self.user_age = (self.created - self._user.birthday()).days


    @property
    def created_str(self):
        return self.created.strftime("%Y-%m-%d")

    @property    
    def user(self):
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

        photo_str = f"{self.nphotos}p" if self.nphotos else ""
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

        return f'Review({self.created_str} {self.uid} {user_str} (rating:{self.rating} {photo_str}) > {self.oid} {title})'