FROM nginx:alpine

RUN rm -f /etc/nginx/conf.d/default.conf

COPY . /usr/share/nginx/html

COPY default.conf /etc/nginx/conf.d/default.conf

EXPOSE 8002

CMD ["nginx", "-g", "daemon off;"]
