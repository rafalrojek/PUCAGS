FROM python

WORKDIR /app
COPY ./grant_revoke.py .
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt
