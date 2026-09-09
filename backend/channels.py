"""Channel setup and offline previews. No external transport or credentials."""
import json
import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class ChannelConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    provider: Literal['Microsoft Teams', 'Slack', 'Other enterprise platform', 'Local test'] = 'Microsoft Teams'
    organization: str = Field(default='', max_length=200)
    destination: str = Field(default='', max_length=200)
    allowed_identities: str = Field(default='', max_length=1000)
    notifications: bool = True
    requests: bool = False
    results: bool = False

class ChannelsMixin:
    def channels_get(self):
        with self.lock:
            row = self.db.execute("SELECT value FROM settings WHERE key='channels_config'").fetchone()
        profiles = json.loads(row[0]) if row else []
        order = {'Microsoft Teams': 0, 'Slack': 1, 'Other enterprise platform': 2, 'Local test': 3}
        return {'profiles': sorted(profiles, key=lambda x: order[x['provider']]), 'live_available': False}

    def channel_save(self, value, cid=None):
        config = ChannelConfig.model_validate(value)
        with self.lock:
            profiles = self.channels_get()['profiles']
            if cid and not any(p['id'] == cid for p in profiles):
                raise ValueError('Channel configuration not found')
            profile = dict(id=cid or uuid.uuid4().hex, **config.model_dump())
            profiles = [p for p in profiles if p['id'] != profile['id']] + [profile]
            self.db.execute("INSERT OR REPLACE INTO settings VALUES('channels_config',?)", (json.dumps(profiles),))
            self.db.commit()
        return profile

    def channel_preview(self, cid):
        profile = next((p for p in self.channels_get()['profiles'] if p['id'] == cid), None)
        if not profile:
            raise ValueError('Channel configuration not found')
        return {'sent': False, 'message': 'Local preview only. No connection was attempted and nothing was sent.',
                'preview': 'Workbench: a sample job is awaiting review. Open your approved Workbench to review it.' if profile['notifications'] else 'Status notifications are disabled in this draft.',
                'requests': 'Not connected. Verified identity mapping and request authorization are required.',
                'results': 'Not connected. Result sharing requires a reviewed data-release policy.'}
