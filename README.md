# ezcov

## packaging
### auto-py-to-exe
> auto-py-to-exe
- add path : customtkinter root
- add file : ezcov_config.yaml, ezcov_theme.json


## version
- [24-02-22]
  - 프로젝트 파일, 
  - 결과 저장 폴더 드래그앤 드랍 구현
  - 메뉴 설정 
  - 에러 핸들링
 
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







