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

# The sidecar launcher looks for <service>/venv/bin/python, so each service gets its own venv.
# TimeManagementAgentService has no requirements.txt of its own; it shares FitnessAgentService's.
COPY chatbot_service/requirements.txt /tmp/req/chatbot.txt
COPY DietPlanService/requirements.txt /tmp/req/diet.txt
COPY FitnessAgentService/requirements.txt /tmp/req/fitness.txt
COPY GymAgentService/requirements.txt /tmp/req/gym.txt
RUN set -e; \
    for pair in chatbot_service:chatbot DietPlanService:diet FitnessAgentService:fitness \
                GymAgentService:gym TimeManagementAgentService:fitness; do \
        svc="${pair%%:*}"; req="${pair##*:}"; \
        python3 -m venv "/app/$svc/venv"; \
        "/app/$svc/venv/bin/pip" install --no-cache-dir -r "/tmp/req/$req.txt"; \
    done

COPY chatbot_service/ chatbot_service/
COPY DietPlanService/ DietPlanService/
COPY FitnessAgentService/ FitnessAgentService/
COPY GymAgentService/ GymAgentService/
COPY TimeManagementAgentService/ TimeManagementAgentService/

WORKDIR /app/VitroFit.API
ENV ASPNETCORE_ENVIRONMENT=Production
# Render injects PORT (default 10000); the shell form expands it at start.
CMD ASPNETCORE_URLS="http://0.0.0.0:${PORT:-10000}" dotnet VitroFit.API.dll
