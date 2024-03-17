# ezcov

## packaging
### auto-py-to-exe
> auto-py-to-exe
- add path : customtkinter root
- add file : ezcov_config.yaml, ezcov_theme.json

## main
![image](https://github.com/Establers/ezcov/assets/44702967/9af40435-f505-4721-bcd1-1f7364160175)

### select develop env
![image](https://github.com/Establers/ezcov/assets/44702967/5ceaa6b5-5d59-4661-92e0-7d9c668693ef)

### configure coverity server setting
![image](https://github.com/Establers/ezcov/assets/44702967/e3af50f1-6095-4693-89f7-2a8b4fd673c1)

 
## sphinx
`pip3 install sphinx`

`sphinx-quickstart --v` : check install
`sphinx-quickstart`

`conf.py`
```py
import os
import sys
sys.path.insert(0, os.path.abspath('../'))

...

extensions = [
    'sphinx.ext.autodoc'
]

...

html_theme = 'sphinx_rtd_theme'
```

`.\make.bat html`







