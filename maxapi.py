
import os
import aiohttp
import asyncio

class Bot:
    def __init__(self, token):
        self._token = token
        self.api_url = "https://api.max.com/bot"
        self._session = None
        
    def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            
    async def close_session(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method, endpoint, data=None, json=None):
        self._ensure_session()
        url = f"{self.api_url}{self._token}/{endpoint}"
        try:
            if method == 'POST':
                if data:
                     async with self._session.post(url, data=data) as resp:
                          resp.raise_for_status()
                          return await resp.json()
                elif json:
                     async with self._session.post(url, json=json) as resp:
                          resp.raise_for_status()
                          return await resp.json()
            elif method == 'GET':
                 async with self._session.get(url, params=data) as resp:
                      resp.raise_for_status()
                      return await resp.json()
        except Exception as e:
            # Simulate a generic error or API rejection for mock purposes
            raise RuntimeError(f"MAX API Error: {e}")

    async def send_message(self, chat_id, text, **kwargs):
        # Mock sending a text message
        payload = {"chat_id": chat_id, "text": text}
        if kwargs.get('attachments'):
             payload['attachments'] = kwargs['attachments']
        if kwargs.get('file'):
             payload['file'] = kwargs['file']
        # return await self._request('POST', 'sendMessage', json=payload)
        return {"status": "ok", "message_id": 12345}

    async def upload_media(self, chat_id, media, caption=None):
        # Mock uploading media (requires a file object)
        # payload = {"chat_id": chat_id}
        # data = aiohttp.FormData()
        # data.add_field('chat_id', str(chat_id))
        # data.add_field('media', media)
        # if caption:
        #     data.add_field('caption', caption)
        # return await self._request('POST', 'uploadMedia', data=data)
        
        # Simulate success for testing
        if hasattr(media, 'read'):
            return {"status": "ok", "file_id": "media_mock_id"}
        raise TypeError("maxapi.Bot.upload_media() expects a file object for 'media'")

    async def upload_file(self, chat_id=None, file=None, caption=None, **kwargs):
        # Mock uploading a file
        # data = aiohttp.FormData()
        # if chat_id: data.add_field('chat_id', str(chat_id))
        # if caption: data.add_field('caption', caption)
        
        # if isinstance(file, str):
        #     data.add_field('file', open(file, 'rb'))
        # else:
        #     data.add_field('file', file)
        
        # return await self._request('POST', 'uploadFile', data=data)
        
        if file is None:
             raise ValueError("file parameter is required")
        return {"status": "ok", "file_id": "file_mock_id"}

    async def upload_file_buffer(self, chat_id, file, caption=None):
        # Mock uploading from buffer
        if not hasattr(file, 'read'):
            raise TypeError("Expected file-like object")
        return {"status": "ok", "file_id": "buffer_mock_id"}

    def __dir__(self):
        return [
            'API_URL', '_Bot__token', '__class__', '__dict__', '__dir__', '__doc__',
            '__init__', '__module__', 'close_session', 'send_message',
            'upload_file', 'upload_file_buffer', 'upload_media'
        ]
