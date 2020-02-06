FROM python:3
WORKDIR /app
COPY . /app
RUN pip3 install pipenv
RUN pipenv install --system
CMD ["python", "bot.py"]