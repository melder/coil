FROM python:3.14.5-alpine3.23

# Install system dependencies
RUN apk add --no-cache \
    build-base curl git nano wget procps htop \
    bash bash-completion nodejs npm \
    jq less ripgrep \
    tree openssh-client bind-tools

# Create non-root user
RUN adduser --disabled-password --gecos '' gemco

# Set Python to use UTF-8 and define a standard locale
# This fixes encoding errors (like 'windows-1252') during pip install
ENV PYTHONUTF8=1
ENV LANG=C.UTF-8

# Configure npm for user-space global installs
# Set these as global ENVs for all subsequent RUN/CMD
ENV NPM_CONFIG_PREFIX=/home/gemco/.npm-global
ENV PATH=$NPM_CONFIG_PREFIX/bin:$PATH

# Switch to non-root user
USER gemco

# Create npm config dir
RUN mkdir -p ~/.npm-global

# Install global Node dependencies
# This layer is cached and runs as 'gemco'
# It does not depend on any application code and will rarely re-run
RUN npm install -g dotenv-cli zx nodemon serve @lvce-editor/ripgrep
RUN npm install -g @google/gemini-cli

# Upgrade pip as a separate, cached layer
RUN pip install --user --upgrade pip

# Set working directory
WORKDIR /app

# Copy and set up bash additions
# This layer is cached and only depends on bashrc.additions
COPY --chown=gemco:gemco bashrc.additions /tmp/
RUN cat /tmp/bashrc.additions >> ~/.bashrc

# Copy ONLY the Python package definition file
# This layer will only re-run if pyproject.toml changes
COPY --chown=gemco:gemco pyproject.toml ./

# Copy the Python source code directory, required for 'pip install -e .'
# This layer will re-run if pyproject.toml or files in 'src' change
COPY --chown=gemco:gemco src ./src

# Install Python dependencies
# This layer is cached and only depends on the files copied above
# The '-e .' install requires the package files
RUN pip install --user -e .

# Copy the rest of the application code
# This layer will invalidate frequently, but it's just a fast copy
# All slow installations above are cached
COPY --chown=gemco:gemco . .

CMD ["bash"]