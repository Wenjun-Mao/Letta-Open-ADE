# Model Catalog

Model Catalog turns Model Router's canonical catalog into feature-ready options.
It exposes `/api/v2/model-catalog/*`, validates feature selections, and supplies
scenario defaults to Agent Studio, Comment Lab, Label Lab, and Test Center.

Model Router is the source of truth for model keys, capability profiles, and
availability. This feature does not read provider configuration directly, create
provider clients, or maintain a second model identity.

`scenario=label` includes active schema metadata through Schema Center's narrow
read contract. All other cross-feature access should use this package's public
selection/options functions rather than internal modules.
