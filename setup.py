from setuptools import setup

APP = ['run.py']
DATA_FILES = []
OPTIONS = {
    'iconfile': 'icon.icns',
    'plist': {
        'LSMinimumSystemVersion': '10.14',
    },
    'packages': [
        'numpy',
        'PIL',
        'yaml',
        'pyobjc_framework_Quartz',
        'pyobjc_framework_ApplicationServices'
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},

)