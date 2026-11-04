FROM nginx:1.27-alpine

COPY ui/ /usr/share/nginx/html/
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

# The HTML is revalidated on every upgrade, while JS/CSS can be immutable.
# Deriving the version from the copied source prevents a forgotten manual
# version bump from serving an old asset after a web image replacement.
RUN set -eu; \
    asset_version="$$(sha256sum \
      /usr/share/nginx/html/index.html \
      /usr/share/nginx/html/app.js \
      /usr/share/nginx/html/styles.css \
      /usr/share/nginx/html/user/index.html \
      /usr/share/nginx/html/user/app.js \
      /usr/share/nginx/html/user/styles.css \
      | sha256sum | cut -c1-16)"; \
    sed -i "s/__AGDA_ASSET_VERSION__/$${asset_version}/g" \
      /usr/share/nginx/html/index.html \
      /usr/share/nginx/html/user/index.html
