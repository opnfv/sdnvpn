import yaml
import os.path
from utils_log import log_enter_exit, for_all_methods
DATABASE_PATH = "/var/lib/home-automation/db.yaml"


class Database:
    @classmethod
    def read_db(cls):
        if not os.path.isfile(DATABASE_PATH):
            return {}
        with open(DATABASE_PATH) as f:
            return yaml.load(f)

    @classmethod
    def save(cls, database_dic):
        with open(DATABASE_PATH, 'w') as f:
            yaml.dump(database_dic, f, default_flow_style=False)

    @classmethod
    def get(cls, path):
        db = cls.read_db()
        paths = path.split('/')
        cls._get_from_dict(db, paths)

    @classmethod
    def _get_from_dict(cls, dic, path):
        if len(path) > 1:
            if path[0] in dic:
                return cls._get_from_dict(dic[path[0]], path[1:])
            else:
                return None
        return dic.get(path[0])

    @classmethod
    def set(cls, path, value):
        db = cls.read_db()
        paths = path.split('/')
        cls._set_from_dict(db, paths, value)
        cls.save(db)

    @classmethod
    def _set_from_dict(cls, dic, path, value):
        if len(path) > 1:
            if path[0] in dic:
                cls._set_from_dict(dic[path[0]], path[1:])
        dic[path[0]] = value
