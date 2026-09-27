"""Harness-issued effective identities; requests cannot select credentials."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Credentials:
    uid: int = 501
    gid: int = 20
    groups: tuple = ()

    @classmethod
    def parse(cls, value=None):
        if value is None:
            return cls()
        if not isinstance(value, dict) or set(value) != {'uid', 'gid', 'groups'}:
            raise ValueError('credentials require uid, gid and supplementary groups')
        groups = value['groups']
        if (not isinstance(groups, list) or len(groups) > 32
                or any(type(number) is not int or not 0 <= number < 2**32 - 1
                       for number in [value['uid'], value['gid'], *groups])
                or len(set(groups)) != len(groups)):
            raise ValueError('invalid simulated credentials')
        return cls(value['uid'], value['gid'], tuple(sorted(groups)))

    def record(self):
        return {'uid': self.uid, 'gid': self.gid, 'groups': list(self.groups)}

    def permissions(self, node):
        if self.uid == 0:
            return 7  # Basic DAC privilege only; protected-path rules still apply.
        if node['uid'] == self.uid:
            return (node['mode'] >> 6) & 7
        if node['gid'] == self.gid or node['gid'] in self.groups:
            return (node['mode'] >> 3) & 7
        return node['mode'] & 7
