# Frontend Web Demo
FROM node:20-buster

#Install apache
RUN apt-get update && \
    apt-get --yes --no-install-recommends install apache2 apache2-dev&& \
    apt-get --yes --purge autoremove apache2-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists \

RUN mkdir /working-directory

# Git submodules are not actual stand-alone repositories when cloned,
# but their .git folder is just a symlink to the parent repository. We need to run git to
# get the current revision, so we have to also add it.
ADD .git /working-directory/.git

#Build frontend node website
ADD swgts-frontend /working-directory/swgts-frontend

RUN cd /working-directory/swgts-frontend && \
    npm install && \
    npm run-script build

RUN a2dissite "*"

# Enable our site in apache
ADD swgts-frontend/apache-site.conf /etc/apache2/sites-available/swgts.conf
RUN a2enmod http2 && \
    a2ensite swgts

RUN mkdir -p /var/www && \
    mv /working-directory/swgts-frontend/build /var/www/swgts

# Ensure the rights are correctly set
RUN chown -R www-data:www-data /var/www/swgts && \
    chmod -R a-w /var/www/swgts

# https://httpd.apache.org/docs/2.4/stopping.html#gracefulstop
STOPSIGNAL SIGWINCH

EXPOSE 80

CMD ["/usr/sbin/apache2ctl","-D","FOREGROUND"]
