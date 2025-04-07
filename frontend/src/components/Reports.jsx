import React, { useState, useEffect } from "react";

const Reports = () => {
    const [downloadUrl, setDownloadUrl] = useState("");

    useEffect(() => {
        fetch("http://127.0.0.1:5000/chatbot/download_report")
            .then(response => response.json())
            .then(data => {
                if (data.download_url) {
                    setDownloadUrl(data.download_url);
                }
            })
            .catch(err => console.error("Error fetching report:", err));
    }, []);

    return (
        <div className="reports-container">
            <h2>Download Analysis Report</h2>
            {downloadUrl ? (
                <a href={`http://127.0.0.1:5000${downloadUrl}`} download>
                    <button>Download Report</button>
                </a>
            ) : (
                <p>No report available yet. Run an analysis first.</p>
            )}
        </div>
    );
};

export default Reports;
