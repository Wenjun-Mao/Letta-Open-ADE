import { AgentCreationForm, type AgentCreationFormProps } from "./agent-creation-form";
import { AgentSelectionControls, type AgentSelectionControlsProps } from "./agent-selection-controls";

type AgentSetupControlsProps = AgentCreationFormProps & AgentSelectionControlsProps;

export function AgentSetupControls(props: AgentSetupControlsProps) {
  return (
    <>
      <AgentCreationForm {...props} />
      <hr className="studio-divider" />
      <AgentSelectionControls {...props} />
    </>
  );
}
