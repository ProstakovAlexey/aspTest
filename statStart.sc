#!/bin/bash
python3 testView.py
tail -n 30 testView.txt>tmp
gnuplot 1.gplt
rm tmp
# пересобрать документацию после изменения картинок
cd doc
make html
cd ..
