# Dockerfile for CLIc server
FROM ubuntu:20.04

LABEL maintainer="clic@jsilber.ca"

RUN apt-get -yqq update && apt-get install -yqq python3 python3-pip net-tools
RUN pip3 install psutil
RUN apt -yqq upgrade

WORKDIR /opt/clicserv/
COPY clic-server.py /opt/clicserv/
COPY acme_chain.pem /opt/clicserv/
COPY acme_key.pem /opt/clicserv/
COPY acme_chain.pem /usr/local/share/ca-certificates
COPY acme_key.pem /usr/local/share/ca-certificates

RUN update-ca-certificates

RUN chmod +x /opt/clicserv/clic-server.py

EXPOSE 33333

CMD ["/opt/clicserv/clic-server.py"]
