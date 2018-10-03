# Changelog

## 0.2.1 (2018-10-03)

- Provide `gmail_download_auth` CLI command to perform authentication flow

## 0.2.0 (2018-06-05)

- Rewrite gmail downloader to simplify code significantly

## 0.1.0 (2017-02-09)

### Features

* Download Gmail e-mail, optionally sorting into folders. See README.md
* Downloading attachments now optional
* Can specify maximum attachment size
* Configuration now in `~/.gmail_query.conf`
* Program creates configuration if none found
* Can update configuration via `setup`
* Can download e-mails to any format supported by `pandoc`
* No sorting if no file is provided

### Known bugs

* Cannot handle multiple attachments.
