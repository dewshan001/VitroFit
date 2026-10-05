# Single container for the whole backend: the .NET API plus the five Python services it launches
# as sidecars (see PythonServiceSidecar in VitroFit.API/Program.cs). Build context = BackendAPI/.

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY VitroFit.API/VitroFit.API.csproj VitroFit.API/
RUN dotnet restore VitroFit.API/VitroFit.API.csproj
COPY VitroFit.API/ VitroFit.API/
RUN dotnet publish VitroFit.API/VitroFit.API.csproj -c Release -o /app/VitroFit.API --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:10.0
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /app/VitroFit.API ./VitroFit.API

# The sidecar launcher uses ONE shared venv at <backend dir>/venv, built from the single requirements.txt.
COPY requirements.txt /tmp/requirements.txt
# CPU-only PyTorch first (sentence-transformers needs it); the default Linux wheel bundles several GB of CUDA libraries.
RUN python3 -m venv /app/venv \
    && /app/venv/bin/pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && /app/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

COPY chatbot_service/ chatbot_service/
COPY DietPlanService/ DietPlanService/
COPY FitnessAgentService/ FitnessAgentService/
COPY GymAgentService/ GymAgentService/
COPY TimeManagementAgentService/ TimeManagementAgentService/

WORKDIR /app/VitroFit.API
ENV ASPNETCORE_ENVIRONMENT=Production
# Render injects PORT (default 10000); the shell form expands it at start.
CMD ASPNETCORE_URLS="http://0.0.0.0:${PORT:-10000}" dotnet VitroFit.API.dll
