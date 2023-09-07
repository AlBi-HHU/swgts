#!/bin/sh

chown www-data:www-data ./output #Give non-root write access to the output folder (create uploads folder, write fastq)
chmod u+rwX ./output
exec /usr/sbin/apache2ctl -D FOREGROUND