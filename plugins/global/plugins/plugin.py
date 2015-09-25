import tega.tree
import tega.subscriber

import subprocess

class GlobalPlugin1(tega.subscriber.PlugIn):

    def __init__(self):
        super().__init__()

    def initialize(self):
        inv = tega.tree.Cont('inventory')
        with self.tx() as t:
            inv.ne1.f5 = self.func(max)
            t.put(inv.ne1.f5)
            inv.ne1.f6 = self.func(self.date)
            t.put(inv.ne1.f6)

    def on_notify(self, notifications):
        pass

    def on_message(self, channel, tega_id, message):
        pass

    def date(self):
        result = subprocess.check_output(['date'])
        return str(result, encoding='utf-8')

