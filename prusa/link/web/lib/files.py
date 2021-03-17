"""Check and modify an input dictionary using recursion"""

from datetime import datetime
from os.path import join

from prusa.connect.printer.metadata import MetaData, estimated_to_seconds
from prusa.connect.printer.const import GCODE_EXTENSIONS

from ..lib.core import app


def get_os_path(abs_path):
    """Gets the OS file path of the file specified by abs_path.

    >>> from mock import Mock
    >>> from prusa.connect.printer.files import Filesystem
    >>> fs = Filesystem()
    >>> fs.from_dir('/tmp', 'Examples')
    >>> app.daemon = Mock()
    >>> app.daemon.prusa_link.printer.fs = fs
    >>> get_os_path('/Examples/not_exist')
    """
    file_system = app.daemon.prusa_link.printer.fs
    file_ = file_system.get(abs_path)
    if not file_:
        return None
    abs_path = abs_path.strip(file_system.sep)
    mount_name = abs_path.split(file_system.sep)[0]
    mount = file_system.mounts[mount_name]
    return file_.abs_path(mount.path_storage)


def files_to_api(node, origin='local', path='/'):
    """Convert Prusa SDK Files tree for API.

    >>> from mock import Mock
    >>> from prusa.connect.printer.files import Filesystem
    >>> fs = Filesystem()
    >>> fs.from_dir('/tmp', 'Prusa Link gcodes')
    >>> fs.get('/Prusa Link gcodes/Examples')
    >>> app.daemon = Mock()
    >>> app.daemon.prusa_link.printer.fs = fs
    >>> files = {'type': 'DIR', 'name': '/', 'ro': True, 'children':[
    ...     {'type': 'DIR', 'name': 'SD Card', 'children':[
    ...         {'type': 'DIR', 'name': 'Examples', 'children':[
    ...             {'type': 'FILE', 'name': '1.gcode'},
    ...             {'type': 'FILE', 'name': 'b.gco'}]}]},
    ...     {'type': 'DIR', 'name': 'Prusa Link gcodes', 'children':[
    ...         {'type': 'DIR', 'name': 'Examples', 'children':[
    ...             {'type': 'FILE', 'name': '1.gcode'},
    ...             {'type': 'FILE', 'name': 'b.gco'}]}]},
    ...     {'type': 'FILE', 'name': 'preview.png'}
    ... ]}
    >>> api_files = files_to_api(files)
    >>> # /
    >>> api_files['type']
    'folder'
    >>> # /SD Card
    >>> api_files['children'][0]['type']
    'folder'
    >>> # /SD Card/Examples
    >>> api_files['children'][0]['children'][0]['type']
    'folder'
    >>> api_files['children'][0]['children'][0]['path']
    '/SD Card/Examples'
    >>> #'/SD Card/Examples/1.gcode'
    >>> api_files['children'][0]['children'][0]['children'][0]['type']
    'machinecode'
    >>> api_files['children'][0]['children'][0]['children'][0]['origin']
    'sdcard'
    >>> # /Prusa Link gcodes/Examples
    >>> api_files['children'][1]['children'][0]['type']
    'folder'
    >>> # /Prusa Link gcodes/Examples/1.gcode
    >>> api_files['children'][1]['children'][0]['children'][0]['type']
    'machinecode'
    >>> api_files['children'][1]['children'][0]['children'][0]['origin']
    'local'
    >>> len(api_files['children'])
    2
    """
    name = node['name']
    path = join(path, name)

    result = {'name': name, 'path': path, 'display': name}

    if "m_time" in node:
        result["date"] = int(datetime(*node['m_time']).timestamp())

    if 'size' in node:
        result['size'] = node['size']

    if node['type'] == 'DIR':
        if name == 'SD Card':
            origin = 'sdcard'

        result['type'] = 'folder'
        result['typePath'] = ['folder']
        result['origin'] = origin
        result['refs'] = {"resource": None}

        children = list(
            files_to_api(child, origin, path)
            for child in node.get("children", []))
        result['children'] = list(child for child in children if child)

    elif name.endswith(GCODE_EXTENSIONS):
        result['origin'] = origin
        result['type'] = 'machinecode'
        result['typePath'] = ['machinecode', 'gcode']
        result['date'] = None
        result['hash'] = None

        if origin != "sdcard":
            # get metadata only for files with cache
            os_path = get_os_path(path)
            meta = MetaData(os_path)
            if os_path and meta.is_cache_fresh():
                meta.load_cache()

            estimated = estimated_to_seconds(
                meta.data.get('estimated printing time (normal mode)', ''))

            result['gcodeAnalysis'] = {
                'estimatedPrintTime': estimated,
                'material': meta.data.get('filament_type'),
                'layerHeight': meta.data.get('layer_height')
                # filament struct
                # dimensions
                # printingArea
            }

            thumbnail = None
            if meta.thumbnails:
                thumbnail = f"/api/thumbnails{path}.orig.png"
            result['refs'] = {
                # 'resource': f"/api/files/local{path}",
                'resource': None,
                'download': f"/api/downloads/local{path}",
                'thumbnailSmall': None,
                'thumbnailBig': thumbnail,
            }
        else:
            result['gcodeAnalysis'] = {
                'estimatedPrintTime': None,
                'material': None,
                'layerHeight': None
            }

            result['refs'] = {
                # 'resource': f"/api/files/local/{path}",
                'resource': None,
                'download': None,
                'thumbnailSmall': None,
                'thumbnailBig': None
            }

    else:
        return {}  # not folder or allowed extension

    return result
