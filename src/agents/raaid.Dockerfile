FROM paulgauthier/aider

USER root
SHELL ["/bin/bash", "-c"]
RUN apt-get update && \
    apt-get install -y ripgrep && \
    . /venv/bin/activate && \
    pip install ra-aid
