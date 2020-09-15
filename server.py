from aiohttp import web
import aiofiles
import asyncio
import os


ZIP_FILE_NAME = 'archive.zip'
PHOTOS_DIRECTORY = 'test_photos'

# Maximum file fragment size to be returned to the user
MAX_FILE_FRAGMENT_SIZE = 100000


async def archivate(request):
    """Zip the desired directory and return to the user"""

    archive_hash = request.match_info.get('archive_hash')
    archive_exists = os.path.exists(f'{PHOTOS_DIRECTORY}/{archive_hash}')
    if not archive_exists:
        raise web.HTTPNotFound(
            text='404: Not Found\n'
                 'The archive does not exist or has been deleted'
        )

    response = web.StreamResponse()

    # Set required headers
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = \
        f'attachment; filename={ZIP_FILE_NAME}'

    # Send HTTP headers to the client
    await response.prepare(request)

    proc = await asyncio.create_subprocess_shell(
        f'cd {PHOTOS_DIRECTORY}/ && zip -r - {archive_hash}',
        stdout=asyncio.subprocess.PIPE,
    )
    while True:
        chunk = await proc.stdout.read(n=MAX_FILE_FRAGMENT_SIZE)

        if chunk == b'':
            return response

        # Send another portion of the response to the client
        await response.write(chunk)


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
