FROM python:3 AS python-setup

WORKDIR /usr/src/app

RUN pip install --no-cache-dir wheel
RUN pip install --no-cache-dir --upgrade pip setuptools

COPY . .
RUN pip install --no-cache-dir .

ENV DEBUG=true
CMD ["kklinux"]
