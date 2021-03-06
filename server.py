from aiohttp import web
from functools import partial
from pathlib import Path
import aiofiles
import asyncio
import logging
import argparse


ZIP_FILE_NAME = 'archive.zip'

# Maximum file fragment size to be returned to the user
MAX_FILE_FRAGMENT_SIZE = 100000


async def archivate(request, directory, delay):
    """Zip the desired directory and return to the user

    * directory - Path to archive with photo
    * delay -Waiting time for response
    """
    archive_hash = request.match_info['archive_hash']
    archive_exists = Path(directory, archive_hash).exists()

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

    zip_command = ['zip', '-r', '-', archive_hash]
    proc = await asyncio.create_subprocess_exec(
        *zip_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=directory,
    )

    try:
        while True:
            chunk = await proc.stdout.read(n=MAX_FILE_FRAGMENT_SIZE)
            logging.info(u'Sending archive chunk ...')

            # For delay response if debug
            await asyncio.sleep(delay)

            if not chunk:
                return response

            # Send another portion of the response to the client
            await response.write(chunk)
    except asyncio.CancelledError:
        logging.error(u'Download was interrupted')
        raise
    finally:
        # Check that the process still exists
        if proc.returncode:
            proc.kill()
            await proc.communicate()

        return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--log',
        action='store_true',
        help='Activate logging'
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=0,
        help='Activate delay for response'
    )
    parser.add_argument(
        '--dir',
        type=str,
        default='test_photos/',
        help='Photo archive directory'
    )
    parser_args = parser.parse_args()

    if parser_args.log:
        logging.basicConfig(level=logging.DEBUG)

    archivate = partial(
        archivate,
        directory=parser_args.dir,
        delay=parser_args.delay,
    )

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
