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

        self._user = user
        self._company = company


        self.created = datetime.datetime.strptime(data['date_created'].split('T')[0], "%Y-%m-%d")
        self.age = (datetime.datetime.now() - self.created).days
        if self._user:
            self.user_age = (self.created - self._user.birthday()).days
        else:
            self.user_age = None

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


    @property
    def created_str(self):
        return self.created.strftime("%Y-%m-%d")

    @property    
    def user(self):
        if self._user:
            return self._user
        from .user import User, get_user
        return get_user(self.uid)

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