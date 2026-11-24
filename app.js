// ============================================================
// TRACEGUARD - FRONTEND
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    const fileInput = document.getElementById("fileInput");
    const analyzeButton = document.getElementById("analyzeButton");
    const fileName = document.getElementById("fileName");

    const loading = document.getElementById("loading");
    const results = document.getElementById("results");

    const attentionBadge =
        document.getElementById("attentionBadge");

    const transactionCount =
        document.getElementById("transactionCount");

    const riskScore =
        document.getElementById("riskScore");

    const flaggedCount =
        document.getElementById("flaggedCount");

    const signalCount =
        document.getElementById("signalCount");

    const priorityScore =
        document.getElementById("priorityScore");

    const priorityMessage =
        document.getElementById("priorityMessage");

    const signalsContainer =
        document.getElementById("signalsContainer");

    const transactionsBody =
        document.getElementById("transactionsBody");


    // ========================================================
    // Check that important elements exist
    // ========================================================

    console.log("TRACEGUARD frontend loaded");

    console.log("fileInput:", !!fileInput);
    console.log("analyzeButton:", !!analyzeButton);
    console.log("loading:", !!loading);
    console.log("results:", !!results);
    console.log("signalsContainer:", !!signalsContainer);
    console.log("transactionsBody:", !!transactionsBody);


    // ========================================================
    // File selection
    // ========================================================

    if (fileInput) {

        fileInput.addEventListener("change", () => {

            if (fileInput.files.length > 0) {

                const file = fileInput.files[0];

                fileName.textContent = file.name;

                console.log(
                    "Selected file:",
                    file.name
                );

            } else {

                fileName.textContent =
                    "No file selected";
            }
        });
    }


    // ========================================================
    // Analyze button
    // ========================================================

    if (analyzeButton) {

        analyzeButton.addEventListener(
            "click",
            analyzeTransactions
        );
    }


    // ========================================================
    // Main analysis
    // ========================================================

    async function analyzeTransactions() {

        console.log(
            "Analyze button clicked"
        );


        // ----------------------------------------------------
        // Check file
        // ----------------------------------------------------

        if (!fileInput ||
            !fileInput.files ||
            fileInput.files.length === 0) {

            alert(
                "Please choose a CSV file first."
            );

            return;
        }


        const file =
            fileInput.files[0];


        if (
            !file.name
                .toLowerCase()
                .endsWith(".csv")
        ) {

            alert(
                "Please upload a CSV file."
            );

            return;
        }


        // ----------------------------------------------------
        // Show loading
        // ----------------------------------------------------

        if (loading) {

            loading.classList.remove("hidden");

            loading.style.display = "flex";
        }


        if (results) {

            results.classList.add("hidden");

            results.style.display = "none";
        }


        if (analyzeButton) {

            analyzeButton.disabled = true;

            analyzeButton.textContent =
                "Analyzing...";
        }


        // ----------------------------------------------------
        // Prepare upload
        // ----------------------------------------------------

        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );


        console.log(
            "Sending CSV to /api/analyze..."
        );


        try {

            // ------------------------------------------------
            // Send CSV to backend
            // ------------------------------------------------

            const response =
                await fetch(
                    "/api/analyze",
                    {
                        method: "POST",
                        body: formData
                    }
                );


            console.log(
                "Backend response status:",
                response.status
            );


            // ------------------------------------------------
            // Read response
            // ------------------------------------------------

            const text =
                await response.text();


            console.log(
                "Backend response:",
                text
            );


            let data;


            try {

                data =
                    JSON.parse(text);

            } catch (jsonError) {

                throw new Error(
                    "The server returned an invalid response."
                );
            }


            // ------------------------------------------------
            // HTTP error
            // ------------------------------------------------

            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    data.message ||
                    "Server error: " +
                    response.status
                );
            }


            // ------------------------------------------------
            // Backend reported failure
            // ------------------------------------------------

            if (
                data.success === false
            ) {

                let message =
                    "Unable to analyze transactions.";

                if (
                    Array.isArray(data.errors) &&
                    data.errors.length > 0
                ) {

                    message =
                        data.errors.join("\n");
                }

                throw new Error(message);
            }


            // ------------------------------------------------
            // Success
            // ------------------------------------------------

            console.log(
                "Analysis successful:",
                data
            );


            displayResults(data);


        } catch (error) {

            console.error(
                "TRACEGUARD analysis error:",
                error
            );


            alert(
                "Analysis failed:\n\n" +
                error.message
            );


        } finally {

            // ------------------------------------------------
            // ALWAYS stop loading
            // ------------------------------------------------

            if (loading) {

                loading.classList.add("hidden");

                loading.style.display = "none";
            }


            if (analyzeButton) {

                analyzeButton.disabled = false;

                analyzeButton.textContent =
                    "Analyze Transactions";
            }


            console.log(
                "Analysis process finished."
            );
        }
    }


    // ========================================================
    // Display results
    // ========================================================

    function displayResults(data) {

        console.log(
            "Displaying results..."
        );


        // ----------------------------------------------------
        // Show results section
        // ----------------------------------------------------

        if (results) {

            results.classList.remove("hidden");

            results.style.display = "block";
        }


        // ----------------------------------------------------
        // Transactions analyzed
        // ----------------------------------------------------

        if (transactionCount) {

            transactionCount.textContent =
                data.transaction_count ?? 0;
        }


        // ----------------------------------------------------
        // Risk score
        // ----------------------------------------------------

        if (riskScore) {

            riskScore.textContent =
                data.risk_score ?? 0;
        }


        // ----------------------------------------------------
        // Flagged count
        // ----------------------------------------------------

        if (flaggedCount) {

            if (
                Array.isArray(
                    data.flagged_transactions
                )
            ) {

                flaggedCount.textContent =
                    data.flagged_transactions.length;

            } else {

                flaggedCount.textContent =
                    data.flagged_transaction_ids
                        ? data.flagged_transaction_ids.length
                        : 0;
            }
        }


        // ----------------------------------------------------
        // Signal count
        // ----------------------------------------------------

        if (signalCount) {

            signalCount.textContent =
                Array.isArray(data.signals)
                    ? data.signals.length
                    : 0;
        }


        // ----------------------------------------------------
        // Attention badge
        // ----------------------------------------------------

        if (attentionBadge) {

            if (data.attention_required) {

                attentionBadge.textContent =
                    "Attention Required";

                attentionBadge.className =
                    "attention-badge attention-required";

            } else {

                attentionBadge.textContent =
                    "No Attention Required";

                attentionBadge.className =
                    "attention-badge no-attention";
            }
        }


        // ----------------------------------------------------
        // Investigator priority
        // ----------------------------------------------------

        if (priorityScore) {

            priorityScore.textContent =
                data.risk_score ?? 0;
        }


        if (priorityMessage) {

            if (data.attention_required) {

                priorityMessage.textContent =
                    "High-priority activity detected. Review the flagged transactions and supporting risk signals first.";

            } else {

                priorityMessage.textContent =
                    "No high-priority unusual activity was detected.";
            }
        }


        // ----------------------------------------------------
        // Risk signals
        // ----------------------------------------------------

        displaySignals(
            data.signals || []
        );


        // ----------------------------------------------------
        // Flagged transactions
        // ----------------------------------------------------

        displayFlaggedTransactions(
            data.flagged_transactions || []
        );


        // ----------------------------------------------------
        // Additional AI report
        // ----------------------------------------------------

        displayInvestigationReport(
            data
        );


        // ----------------------------------------------------
        // Scroll to results
        // ----------------------------------------------------

        if (results) {

            setTimeout(() => {

                results.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });

            }, 100);
        }
    }


    // ========================================================
    // Risk signals
    // ========================================================

    function displaySignals(signals) {

        if (!signalsContainer) {
            return;
        }


        if (
            !Array.isArray(signals) ||
            signals.length === 0
        ) {

            signalsContainer.innerHTML = `
                <div class="empty-state">
                    No risk signals detected.
                </div>
            `;

            return;
        }


        signalsContainer.innerHTML =
            signals.map(
                signal => {

                    const rule =
                        escapeHtml(
                            signal.rule ||
                            "Risk Signal"
                        );


                    const severity =
                        escapeHtml(
                            signal.severity ||
                            "UNKNOWN"
                        );


                    const explanation =
                        escapeHtml(
                            signal.explanation ||
                            ""
                        );


                    const ids =
                        Array.isArray(
                            signal.transaction_ids
                        )
                            ? signal.transaction_ids
                            : [];


                    const transactionTags =
                        ids.map(
                            id => `
                                <span class="transaction-tag">
                                    ${escapeHtml(id)}
                                </span>
                            `
                        ).join(" ");


                    return `
                        <div class="signal-card">

                            <div class="signal-header">

                                <strong>
                                    ${rule}
                                </strong>

                                <span class="severity ${severity.toLowerCase()}">
                                    ${severity}
                                </span>

                            </div>

                            <p>
                                ${explanation}
                            </p>

                            <div class="signal-transactions">
                                ${transactionTags}
                            </div>

                        </div>
                    `;
                }
            ).join("");
    }


    // ========================================================
    // Flagged transactions
    // ========================================================

    function displayFlaggedTransactions(
        transactions
    ) {

        if (!transactionsBody) {
            return;
        }


        if (
            !Array.isArray(transactions) ||
            transactions.length === 0
        ) {

            transactionsBody.innerHTML = `
                <tr>
                    <td colspan="6">
                        No flagged transactions.
                    </td>
                </tr>
            `;

            return;
        }


        transactionsBody.innerHTML =
            transactions.map(
                tx => {

                    return `
                        <tr>

                            <td>
                                <strong>
                                    ${escapeHtml(
                                        tx.transaction_id
                                    )}
                                </strong>
                            </td>

                            <td>
                                ${escapeHtml(
                                    tx.date
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    tx.description
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    tx.payee
                                )}
                            </td>

                            <td>
                                ₹${formatAmount(
                                    tx.amount
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    tx.channel
                                )}
                            </td>

                        </tr>
                    `;
                }
            ).join("");
    }


    // ========================================================
    // Investigation report
    // ========================================================

    function displayInvestigationReport(data) {

        // The current HTML does not have a dedicated
        // investigation report element.
        //
        // Therefore create one automatically.

        if (!results) {
            return;
        }


        let report =
            document.getElementById(
                "traceguardReport"
            );


        if (!report) {

            report =
                document.createElement(
                    "div"
                );

            report.id =
                "traceguardReport";

            report.className =
                "investigation-report";


            const priorityCard =
                results.querySelector(
                    ".priority-card"
                );


            if (priorityCard) {

                priorityCard.after(
                    report
                );

            } else {

                results.prepend(
                    report
                );
            }
        }


        let html = "";


        // ----------------------------------------------------
        // Gemini report
        // ----------------------------------------------------

        if (
            data.gemini_success &&
            data.investigation_report
        ) {

            html += `
                <div class="report-card">

                    <p class="eyebrow">
                        AI INVESTIGATION
                    </p>

                    <h3>
                        Gemini Investigation Report
                    </h3>

                    <div class="report-content">
                        ${formatReport(
                            data.investigation_report
                        )}
                    </div>

                </div>
            `;

        } else {

            // ------------------------------------------------
            // Deterministic fallback
            // ------------------------------------------------

            html += `
                <div class="report-card">

                    <p class="eyebrow">
                        INVESTIGATION FINDINGS
                    </p>

                    <h3>
                        Deterministic Risk Assessment
                    </h3>

                    <p>
                        TraceGuard detected
                        <strong>
                            ${data.flagged_transactions
                                ? data.flagged_transactions.length
                                : 0}
                        </strong>
                        flagged transaction(s)
                        across
                        <strong>
                            ${data.signals
                                ? data.signals.length
                                : 0}
                        </strong>
                        risk signal(s).
                    </p>

                    <p>
                        The activity should be reviewed by
                        a qualified human investigator.
                    </p>

                </div>
            `;
        }


        // ----------------------------------------------------
        // Gemini error
        // ----------------------------------------------------

        if (data.gemini_error) {

            html += `
                <div class="gemini-warning-box">

                    <strong>
                        AI explanation unavailable
                    </strong>

                    <p>
                        The deterministic risk findings
                        above are still available.
                    </p>

                    <small>
                        ${escapeHtml(
                            data.gemini_error
                        )}
                    </small>

                </div>
            `;
        }


        report.innerHTML =
            html;
    }


    // ========================================================
    // Format report
    // ========================================================

    function formatReport(text) {

        if (!text) {
            return "";
        }


        let formatted =
            escapeHtml(text);


        // Bold markdown
        formatted =
            formatted.replace(
                /\*\*(.*?)\*\*/g,
                "<strong>$1</strong>"
            );


        // Numbered headings
        formatted =
            formatted.replace(
                /^(\d+\.\s+)(.+)$/gm,
                "<h4>$1$2</h4>"
            );


        // Bullet points
        formatted =
            formatted.replace(
                /^[-•]\s+(.+)$/gm,
                "<li>$1</li>"
            );


        // Paragraph breaks
        formatted =
            formatted.replace(
                /\n\n/g,
                "<br><br>"
            );


        // Single line breaks
        formatted =
            formatted.replace(
                /\n/g,
                "<br>"
            );


        return formatted;
    }


    // ========================================================
    // Format amount
    // ========================================================

    function formatAmount(amount) {

        const number =
            Number(amount);


        if (
            Number.isNaN(number)
        ) {

            return "0.00";
        }


        return number.toLocaleString(
            "en-IN",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        );
    }


    // ========================================================
    // Escape HTML
    // ========================================================

    function escapeHtml(value) {

        if (
            value === null ||
            value === undefined
        ) {

            return "";
        }


        return String(value)
            .replace(
                /&/g,
                "&amp;"
            )
            .replace(
                /</g,
                "&lt;"
            )
            .replace(
                />/g,
                "&gt;"
            )
            .replace(
                /"/g,
                "&quot;"
            )
            .replace(
                /'/g,
                "&#039;"
            );
    }

});