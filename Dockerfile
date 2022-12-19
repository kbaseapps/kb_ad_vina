FROM kbase/sdkpython:3.8.0
MAINTAINER KBase Developer

ENV KBASE_CONTAINER=yes
RUN apt-get update
RUN apt-get install -y autodock-vina openbabel

WORKDIR /kb/module

# python requirements
COPY ./requirements.txt /kb/module/requirements.txt
ENV PIP_PROGRESS_BAR=off
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install git+https://github.com/kbase-sfa-2021/sfa.git@5d663ef13417bef10d449664de6c99b310816c95

# node and node requirements
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get install -y nodejs
COPY ./package.json /kb/module/package.json
RUN npm install --production

COPY ./ /kb/module
RUN npm run build

RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
