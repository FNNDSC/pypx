#
# Dockerfile for pypx repository.
#
# Build with
#
#   docker build -t <name> .
#
# For example if building a local version, you could do:
#
#   docker build --build-arg UID=$UID -t local/pypx .
#
# In the case of a proxy (located at say 10.41.13.4:3128), do:
#
#    export PROXY="http://10.41.13.4:3128"
#    docker build --build-arg http_proxy=${PROXY} --build-arg UID=$UID -t local/pypx .
#
# To run an interactive shell inside this container, do:
#
#   docker run -ti --entrypoint /bin/bash local/pypx
#
# To pass an env var HOST_IP to container, do:
#
#   docker run -ti -e HOST_IP=$(ip route | grep -v docker | awk '{if(NF==11) print $9}') \
#              --entrypoint /bin/bash local/pypx
#
# To run a specific bin with volume mapping for debug purposes:
#


FROM fnndsc/ubuntu-python3:latest

LABEL fnndsc="dev@babymri.org"
LABEL DEBUG_EXAMPLE="                                                   \
docker run  --rm -ti                                                    \
            -e HOST_IP=$(ip route | grep -v docker | awk '{if(NF==11) print $9}')      \
            -v $(pwd)/pypx:/usr/local/lib/python3.6/dist-packages/pypx  \
            -v $(pwd)/bin/px-echo:/usr/local/bin/px-echo                \
            -v $(pwd)/bin/px-find:/usr/local/bin/px-find                \
            -v $(pwd)/bin/px-move:/usr/local/bin/px-move                \
            -v $(pwd)/bin/px-listen:/usr/local/bin/px-listen            \
            local/pypx                                                  \
            --px-find                                                   \
            --aet CHIPS                                                 \
            --aec ORTHANC                                               \
            --serverIP  10.72.76.155                                    \
            --serverPort 4242                                           \
            --patientID LILLA-9731                                      \
\
        docker run  --rm -ti                                            \
            -e HOST_IP=$(ip route | grep -v docker | awk '{if(NF==11) print $9}')      \
            -v $(pwd)/pypx:/usr/local/lib/python3.6/dist-packages/pypx  \
            -v $(pwd)/bin/px-echo:/usr/local/bin/px-echo                \
            -v $(pwd)/bin/px-find:/usr/local/bin/px-find                \
            -v $(pwd)/bin/px-move:/usr/local/bin/px-move                \
            -v $(pwd)/bin/px-listen:/usr/local/bin/px-listen            \
            local/pypx                                                  \
            --px-find                                                   \
            --aec CHRIS                                                 \
            --aet FNNDSC-CHRISDEV                                       \
            --serverIP 134.174.12.21                                    \
            --serverPort 104                                            \
            --patientID 4777764                                         \
"

# Pass a UID on build command line (see above) to set internal UID
ARG UID=1001
ENV UID=$UID

ARG APPROOT="/usr/src/pfdcm"  
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
  && pip3 install /tmp/pypx                                           \
  && rm -fr /tmp/pypx
  
COPY ./docker-entrypoint.py /dock/docker-entrypoint.py
COPY ./dicomlistener /etc/xinetd.d 
RUN chmod 777 /dock                                                   \
  && chmod 777 /dock/docker-entrypoint.py                             \
  && echo "localuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers          \
  && service xinetd restart

ENTRYPOINT ["/dock/docker-entrypoint.py"]
EXPOSE 4055 10402

# Start as user $UID
# USER $UID

