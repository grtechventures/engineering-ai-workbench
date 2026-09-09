# Example walkthrough

Complete [Windows 11 setup](README.md#windows-11-setup), then open http://127.0.0.1:8765. A local model enables conversation and script drafting; demo-mode agents and released calculations work without a model. Docker is needed only for reviewed Python extensions.

## Conversation and comparison

1. Create a starter agent, or create an agent in **Agents**, selecting demo or local mode.
2. Ask “Compare Run A and Run B.” Review and approve the plan.
3. Inspect the chart, metrics and inputs. Accept the report after reviewing the synthetic evidence.
4. Ask what RMSE means. Model prose is a draft; the numerical result remains unchanged.
5. In **Evidence**, download the record or choose **Replay saved inputs**. This creates a linked job with fresh reviews.

## Project memory

1. Open **Reviewed knowledge**. Propose “RMSE and maximum difference should be reported together,” with a source such as “Example review convention.”
2. Approve the note, then search for RMSE.
3. Start a conversation and ask about RMSE. The retrieved-reference panel shows the source and revision. Demo mode displays the matched note; local mode receives it as reference context.
4. Retire the note and search again. It is excluded from new retrievals; historical conversations remain available.

## Bounded study

1. Open an accepted comparison without a generated extension. Choose **Evidence → Explore smoothing parameters**.
2. Propose windows 1, 3, 5 and 9 with a five-second budget.
3. Review the plan and approve execution. This runs released Python, not generated code.
4. Compare distortion and roughness. There is deliberately no automatic engineering winner.
5. Accept the study results and download its evidence. Reopen studies through **Job history → Load saved studies**.

## Reviewed code and reusable skills

Ask “Smooth the difference using a five-sample moving average.” Approve the plan, inspect the exact Python script, then approve execution in the configured Docker worker. All output samples must match the independent reference. The Evidence view retains the execution receipt after container removal.

Accept a report and choose **Propose reusable skill**. Review the candidate separately before releasing it. Running the recipe uses authorized inputs and retains code-review requirements. A recipe is not permission to execute arbitrary code.

## Deployment notes

The reference workspace has one local reviewer and synthetic inputs. Windows runtime verification is pending; consult [VALIDATION.md](VALIDATION.md). Do not present this as a multi-user production deployment. Installations do not require a GitHub account; source archives can be distributed through approved internal channels.

## Scheduled workflow

From an accepted released comparison, open **Evidence → Schedule this workflow**. Select an agent with the released comparison skill assigned. Choose Once, UTC, and a future time several minutes ahead. Save the proposal, inspect its recipe and limits, and approve it. Keep the service running.

Open **Schedules**. After the occurrence, expand Run history and open the result. The approved comparison executes without a second plan prompt, but the result awaits acceptance. Daily/weekly schedules skip the next occurrence if a prior result is still awaiting review. Pause, resume and cancel controls are available for recurring schedules.
