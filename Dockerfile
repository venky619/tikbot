FROM registry.gitlab.com/fronbasal/docker-pipenv
WORKDIR /app
COPY . /app
RUN pipenv install --system
CMD ["python", "bot.py"]