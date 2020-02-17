FROM python:3.6.0-onbuild
WORKDIR /app
ADD . /app
RUN pip install -r /app/requirements.txt --ignore-installed
ENV PORT 8888
EXPOSE $PORT
CMD python /app/run.py