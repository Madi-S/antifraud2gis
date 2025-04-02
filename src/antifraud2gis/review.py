import datetime
from rich import print_json

class Review():
    def __init__(self, data):    
        self._data = data
        self.review_id = data['id']
        self.rating = data['rating']
        self.oid = data['object']['id']
        self.uid = data['user']['public_id']
        self.user_name = data['user']['name']
        self.text = data.get('text')        
        self.nphotos = len(data['photos'])
        
        self.created = datetime.datetime.strptime(data['date_created'].split('T')[0], "%Y-%m-%d")
        self.age = (datetime.datetime.now() - self.created).days

        try:
            self.title = data['object']['name']
        except KeyError:
            self.title = None
        try:
            self.address = data['object']['address']
        except KeyError:
            self.address = None


    def is_visible(self):
        return True

        #if self.uid != '06ca4d2e9b404411b6e47bdb464cee8b':
        #    return True
        
        c = Company(self.oid)
        c.load_reviews()
        cu = list(c.uids())
        # print(cu)
        
        #print("VIS:", self.uid in cu)
        #print("visible?", self.uid, self.oid)
        return self.uid in cu

    @property
    def user(self):
        from .user import User
        return User(self.uid)

    @property
    def user_url(self):
        return f'https://2gis.ru/x/user/{self.uid}'


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

        return f'Review( {self.uid} {user_str} (rating:{self.rating} {photo_str}) > {self.oid} {title})'