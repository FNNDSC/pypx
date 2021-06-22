#
# Dockerfile for pypx repository.
#
# Build with
#
#   DOCKER_BUILDKIT=1  docker build -t <name> .
#
# For example if building a local version, you could do:
#
#   DOCKER_BUILDKIT=1 docker build --build-arg UID=$UID -t local/pypx .
#
# In the case of a proxy (located at say 10.41.13.4:3128), do:
#
#    export PROXY="http://proxy.tch.harvard.edu:3128"
#    DOCKER_BUILDKIT=1  docker build --build-arg http_proxy=${PROXY} --build-arg UID=$UID -t local/pypx .
#
# To run an interactive shell inside this container, do:
#
#   docker run -ti --entrypoint /bin/bash local/pypx
#
#


FROM fnndsc/ubuntu-python3:latest

LABEL fnndsc="dev@babymri.org"
LABEL DEBUG_EXAMPLE="                                                       \
docker run  --rm -ti                                                        \
            -e HOST_IP=$(ip route | grep -v docker | awk '{if(NF==11) print $9}')      \
            -v $PWD/pypx:/usr/local/lib/python3.8/dist-packages/pypx        \
            -v $PWD/bin/px-do:/usr/local/bin/px-do                          \
            -v $PWD/bin/px-echo:/usr/local/bin/px-echo                      \
            -v $PWD/bin/px-find:/usr/local/bin/px-find                      \
            -v $PWD/bin/px-move:/usr/local/bin/px-move                      \
            -v $PWD/bin/px-listen:/usr/local/bin/px-listen                  \
            -v $PWD/bin/px-push:/usr/local/bin/px-push                      \
            -v $PWD/bin/px-register:/usr/local/bin/px-register              \
            -v $PWD/bin/px-report:/usr/local/bin/px-report                  \
            -v $PWD/bin/px-smdb:/usr/local/bin/px-smdb                      \
            -v $PWD/bin/px-status:/usr/local/bin/px-status                  \
            -v $PWD/dicom:/home/dicom                                       \
            local/pypx                                                      \
            -p 11113:11113                                                  \
            --px-find                                                       \
            --aet CHRISLOCAL                                                \
            --aec ORTHANC                                                   \
            --serverIP  192.168.1.189                                       \
            --serverPort 4242                                               \
            --patientID 4780041                                             \
            --db /home/dicom/log                                            \
            --verbosity 1                                                   \
            --json                                                          \
                                                                            \
        docker run  --rm -ti                                                \
            -e HOST_IP=$(ip route | grep -v docker | awk '{if(NF==11) print $9}')      \
            -v $PWD/pypx:/usr/local/lib/python3.8/dist-packages/pypx        \
            -v $PWD/bin/px-do:/usr/local/bin/px-do                          \
            -v $PWD/bin/px-echo:/usr/local/bin/px-echo                      \
            -v $PWD/bin/px-find:/usr/local/bin/px-find                      \
            -v $PWD/bin/px-move:/usr/local/bin/px-move                      \
            -v $PWD/bin/px-listen:/usr/local/bin/px-listen                  \
            -v $PWD/bin/px-push:/usr/local/bin/px-push                      \
            -v $PWD/bin/px-register:/usr/local/bin/px-register              \
            -v $PWD/bin/px-report:/usr/local/bin/px-report                  \
            -v $PWD/bin/px-smdb:/usr/local/bin/px-smdb                      \
            -v $PWD/bin/px-status:/usr/local/bin/px-status                  \
            -v $PWD/dicom:/home/dicom                                       \
            local/pypx                                                      \
            -p 11113:11113                                                  \
            --px-find                                                       \
            --aec CHRIS                                                     \
            --aet FNNDSC-CHRISDEV                                           \
            --serverIP 134.174.12.21                                        \
            --serverPort 104                                                \
            --patientID 4777764                                             \
"

# Pass a UID on build command line (see above) to set internal UID
ARG UID=1001
ENV UID=$UID
ENV LISTENPORT=$LISTENPORT

COPY . /tmp/pypx
COPY ./docker-entrypoint.py /dock/docker-entrypoint.py

RUN apt-get update \
  && apt-get install sudo                                             \
  && useradd -u $UID -ms /bin/bash localuser                          \
  && addgroup localuser sudo                                          \
  && echo "localuser:localuser" | chpasswd                            \
  && adduser localuser sudo                                           \
  && apt-get install -y libssl-dev libcurl4-openssl-dev bsdmainutils vim net-tools inetutils-ping \
  && apt-get install -y netcat-openbsd xinetd                         \
  && apt-get install -y dcmtk                                         \
  && pip install --upgrade pip                                        \
  && pip install /tmp/pypx                                            \
  && rm -fr /tmp/pypx

COPY ./docker-entrypoint.py /dock/docker-entrypoint.py
COPY ./storescp.sh /dock/storescp.sh
RUN chmod 777 /dock                                                   \
  && chmod 777 /dock/docker-entrypoint.py                             \
  && echo "localuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

ENTRYPOINT ["/dock/docker-entrypoint.py"]
CMD ["/dock/storescp.sh", "-p", "11113"]
EXPOSE 11113

# Start as user $UID
# USER $UID

