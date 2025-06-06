class Column(list):
    def unique(self):
        return list(dict.fromkeys(self))

class DataFrame:
    def __init__(self, data=None, columns=None):
        if isinstance(data, dict):
            self.columns = list(data.keys())
            length = len(next(iter(data.values()))) if data else 0
            self._data = [dict(zip(self.columns, row)) for row in zip(*data.values())]
        elif isinstance(data, list):
            if data and isinstance(data[0], dict):
                self.columns = columns or list(data[0].keys())
                self._data = [ {k: row.get(k) for k in self.columns} for row in data ]
            else:
                self.columns = columns or []
                self._data = data
        else:
            self.columns = columns or []
            self._data = []

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return Column([row[key] for row in self._data])

    def to_excel(self, *args, **kwargs):
        # noop for stub
        pass

api = type('api', (), {'types': type('types', (), {})})()

def to_datetime(obj, errors="raise", utc=False):
    return obj
