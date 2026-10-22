import re, pathlib
here = pathlib.Path(__file__).parent
s = (here.parent / 'src' / 'slip-scanner.html').read_text()
js = re.search(r'<script>\n(.*)</script>\s*$', s, re.S).group(1)
pure = js.split('/*PURE-START*/')[1].split('/*PURE-END*/')[0]
(here / '_script.js').write_text(js)
(here / '_pure.js').write_text(pure + '\nmodule.exports={pad,solveLinear,homography,slug,parseNum,normDate,dupKey,fileBase,buildPath,nextRegNo,csvCell};')
