import type { CreateTestRunPayload } from "./api";
import type { TestCenterCopy } from "./test-center-copy";

type Props = {
  copy: TestCenterCopy;
  busy: boolean;
  onCreateRun: (payload: CreateTestRunPayload) => void;
};

export function CurrentStackSmokeLauncher(props: Props) {
  return (
    <div className="card">
      <p className="muted">{props.copy.smokeHelp}</p>
      <button className="button" disabled={props.busy} onClick={() => props.onCreateRun({ run_type: "ade_api_e2e_check" })}>
        {props.busy ? props.copy.submitting : props.copy.createRun}
      </button>
    </div>
  );
}
