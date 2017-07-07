sandcastle
==========

This is a Django project which allows you to test pull requests from your browser.

Deprecated
----------
This project is no longer in use at Khan Academy.

Configuration
-------------

Specify your repository by setting `SANDCASTLE_USER` and
`SANDCASTLE_REPO` in `settings.py`. For example, setting up sandcastle
for this repository would look like:

    SANDCASTLE_USER = 'jpulgarin'
    SANDCASTLE_REPO = 'sandcastle'

Used At
-------

It was in use at [Khan Academy](http://www.khanacademy.org) to
test pull requests to their exercise framework, but is no longer used for that purpose.
