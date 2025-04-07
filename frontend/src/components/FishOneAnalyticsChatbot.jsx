import React, { useState, useRef, useEffect } from "react";
import { Settings, RefreshCw } from "lucide-react";
import ReactMarkdown from "react-markdown";
// // import { toast } from 'react-toastify';
// import 'react-toastify/dist/ReactToastify.css';
import axios from "axios";
import { Table } from "antd";
import "../styles/Chatbot.css";



const ChatbotPage = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "bot",
      content:
        "Welcome to Karatos! I can help you analyze defects in your manufacturing process. What would you like to know?",
      timestamp: new Date(),
    },
  ]);

  const [inputMessage, setInputMessage] = useState("");
  const [isParameterPanelOpen, setIsParameterPanelOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [showVoicePopup, setShowVoicePopup] = useState(false);

  

  const [analysisParams, setAnalysisParams] = useState({
    companyName: "",
    defectType: "",
    groupName: "",
    components: [],
    isComponentWise: false,
  });

  const [dropdownOptions, setDropdownOptions] = useState({
    defectOptions: [],
    groupOptions: [],
    componentOptions: [],
  });

  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (analysisParams.companyName) {
      axios
        .get("http://127.0.0.1:5000/get_dropdown_options", {
          params: { foundry: analysisParams.companyName.trim() },
        })
        .then((response) => {
          setDropdownOptions(response.data);
        })
        .catch((error) => {
          console.error(" Error fetching dropdown options:", error);
          setDropdownOptions({ defectOptions: [], groupOptions: [], componentOptions: [] });
        });
    }
  }, [analysisParams.companyName]);



  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
        id: Date.now(),
        type: "user",
        content: inputMessage,
        timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setLoading(true);

    try {
        const response = await axios.post(
            "http://127.0.0.1:5000/chatbot/ask",
            { query: inputMessage.trim() },
            { headers: { "Content-Type": "application/json" } }
        );

        const { response: botResponse } = response.data;
        let botMessages = [];

        // // Fix Issue 1: Only push valid messages
        // if (botResponse.messages && Array.isArray(botResponse.messages)) {
        //     botMessages = botResponse.messages
        //         .filter((msg) => msg.trim() !== "I didn't understand that.")
        //         .map((msg, index) => ({
        //             id: Date.now() + index + 1,
        //             type: "bot",
        //             content: msg,
        //             timestamp: new Date(),
        //         }));
        // }

        // Handle Summary Text
        if (botResponse.summary && botResponse.summary.messages) {
            botResponse.summary.messages.forEach((msg, index) => {
                botMessages.push({
                    id: Date.now() + botMessages.length + 2 + index,
                    type: "bot",
                    content: msg,
                    timestamp: new Date(),
                });
            });
        }

        // Handle Summary Table
        if (botResponse.summary && botResponse.summary.summary_table && Array.isArray(botResponse.summary.summary_table.data)) {
            botMessages.push({
                id: Date.now() + botMessages.length + 1,
                type: "bot",
                content: "Summary Table",
                timestamp: new Date(),
            });

            const tableData = botResponse.summary.summary_table.data.map((item, index) => ({
                key: index + 1,
                parameter: item.parameter,
                absolute_change: item.absolute_change !== null ? item.absolute_change.toFixed(2) + "%" : "0.00%",
            }));

            const tableColumns = [
                { title: "Parameter", dataIndex: "parameter", key: "parameter" },
                { title: "Absolute Change (%)", dataIndex: "absolute_change", key: "absolute_change" },
            ];

            botMessages.push({
                id: Date.now() + botMessages.length + 1,
                type: "bot",
                isTable: true,
                tableData,
                tableColumns,
                timestamp: new Date(),
            });
        }

        // Handle Summary Chart
        if (botResponse.summary && botResponse.summary.summary_chart && botResponse.summary.summary_chart !== "No Summary Chart Available") {
            botMessages.push({
                id: Date.now() + botMessages.length + 1,
                type: "bot",
                content: "Summary Chart",
                timestamp: new Date(),
            });

            botMessages.push({
                id: Date.now() + botMessages.length + 1,
                type: "bot",
                isImage: true,
                imageUrl: botResponse.summary.summary_chart,
                timestamp: new Date(),
            });
        }

        // Handle Rejection Table
        if (botResponse.rejection_data && Array.isArray(botResponse.rejection_data)) {
            botMessages.push({
                id: Date.now() + botMessages.length + 1,
                type: "bot",
                content: "Rejection Data Table",
                timestamp: new Date(),
            });

            const tableData = botResponse.rejection_data.map((item, index) => ({
                key: index + 1,
                month: item.month,
                rejection_percentage: item.rejection_percentage.toFixed(4),
            }));

            const tableColumns = [
                { title: "Month", dataIndex: "month", key: "month" },
                { title: "Rejection %", dataIndex: "rejection_percentage", key: "rejection_percentage" },
            ];

            botMessages.push({
                id: Date.now() + botMessages.length + 1,
                type: "bot",
                isTable: true,
                tableData,
                tableColumns,
                timestamp: new Date(),
            });
        }
        

        // Handle Rejection Trend Chart
        if (botResponse.Chart && botResponse.Chart !== "No Chart Available") {
            botMessages.push({
                id: Date.now() + botMessages.length + 1,
                type: "bot",
                content: "Rejection Trend Chart",
                timestamp: new Date(),
            });
            // speakText("Here is the Rejection Trend Chart.");

            botMessages.push({
                id: Date.now() + botMessages.length + 1,
                type: "bot",
                isImage: true,
                imageUrl: botResponse.Chart,
                timestamp: new Date(),
            });
        }




        // Handle Fishbone Chart
        if (botResponse["FBA Chart"] && botResponse["FBA Chart"] !== "No FBA Chart Available") {
            botMessages.push({
                id: Date.now() + botMessages.length + 1,
                type: "bot",
                content: "Fishbone Diagram",
                timestamp: new Date(),
            });
            
            // speakText("Here is the Fishbone Diagram.");


            botMessages.push({
                id: Date.now() + botMessages.length + 1,
                type: "bot",
                isImage: true,
                imageUrl: botResponse["FBA Chart"],
                timestamp: new Date(),
            });

        }

    
        // Append text messages
        if (botResponse.messages && Array.isArray(botResponse.messages)) {
          const msgObjects = botResponse.messages.map((msg, index) => ({
            id: Date.now() + index + 1,
            type: "bot",
            content: msg,
            timestamp: new Date(),
          }));
        
          setMessages((prev) => [...prev, ...msgObjects]);
        }

        // Handle Reference, Comparison Period, and Top Parameter if present
        if (botResponse.summary || botResponse.top_parameter || botResponse.reference_period || botResponse.comparison_period) {
          let metaMessages = [];

          if (botResponse.reference_period) {
              metaMessages.push(
                  `📌 Reference Period: **${botResponse.reference_period[0]}** to **${botResponse.reference_period[1]}**`
              );
          }

          if (botResponse.comparison_period) {
              metaMessages.push(
                  `📌 Comparison Period: **${botResponse.comparison_period[0]}** to **${botResponse.comparison_period[1]}**`
              );
          }

          if (botResponse.top_parameter) {
              metaMessages.push(`📊 Top varied parameter: **${botResponse.top_parameter}**`);
          }

          metaMessages.forEach((msg, index) => {
              botMessages.push({
                  id: Date.now() + 500 + index,
                  type: "bot",
                  content: msg,
                  timestamp: new Date(),
              });
          });
        }


    
        if (botResponse.charts && Array.isArray(botResponse.charts)) {
          const chartObjects = botResponse.charts.map((url, index) => {
            const bustedUrl = url.includes("?t=")
              ? url
              : `${url}?t=${Date.now()}`;
        
            return {
              id: Date.now() + 100 + index,
              type: "bot",
              isImage: true,
              imageUrl: bustedUrl,
              timestamp: new Date(),
            };
          });
        
          if (chartObjects.length > 0) {
            setMessages((prev) => [
              ...prev,
              {
                id: Date.now() + 999,
                type: "bot",
                content: "Here is the chart you requested!",
                timestamp: new Date(),
              },
              ...chartObjects,
            ]);
            speakWithElevenLabs("Here is the chart you requested.");

          }
        }
  
        if (botResponse.chart_blocks && Array.isArray(botResponse.chart_blocks)) {
          botResponse.chart_blocks.forEach((block, index) => {
            if (block.message) {
              botMessages.push({
                id: Date.now() + botMessages.length + 1 + index,
                type: "bot",
                content: block.message,
                timestamp: new Date(),
              });
            }

            if (block.image) {
              botMessages.push({
                id: Date.now() + botMessages.length + 1 + index,
                type: "bot",
                isImage: true,
                imageUrl: block.image.includes("?t=")
                  ? block.image
                  : `${block.image}?t=${Date.now()}`,
                timestamp: new Date(),
              });
            }
          });
        }

        if (botResponse.report) {
          botMessages.push({
              id: Date.now() + 1000,
              type: "bot",
              content: "📄 Here is your downloadable report:",
              timestamp: new Date(),
          });
          botMessages.push({
              id: Date.now() + 1001,
              type: "bot",
              isLink: true,
              linkText: "Download Report",
              linkUrl: botResponse.report,
              timestamp: new Date(),
          });
        }

        

        setMessages((prev) => [...prev, ...botMessages]);
        speakWithElevenLabs(botResponse.messages.join(" "));


        
      

    } catch (error) {
        console.error("API Error:", error.response ? error.response.data : error.message);
        setMessages((prev) => [
            ...prev,
            {
                id: Date.now(),
                type: "bot",
                content: "Error reaching the server.",
                timestamp: new Date(),
            },
        ]);
    }
    

    setLoading(false);
};



useEffect(() => {
  messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
}, [messages]);




  const handleSelectionChange = async (key, value) => {
    const updatedParams = { ...analysisParams, [key]: value };
  
    if (key === "groupName") {
      try {
        const response = await axios.get("http://127.0.0.1:5000/get_dropdown_options", {
          params: { foundry: updatedParams.companyName.trim() },
        });
  
        updatedParams.components = response.data.groupOptions[value] || [];
      } catch (error) {
        console.error("Error fetching components for selected group:", error);
        updatedParams.components = [];
      }
    }
  
    setAnalysisParams(updatedParams);
  
    try {
      await axios.post(
        "http://127.0.0.1:5000/update_analysis_selection",
        {
          foundry: updatedParams.companyName,
          defect: updatedParams.defectType,
          group: updatedParams.groupName,
          components: updatedParams.components,
          isComponentWise: updatedParams.isComponentWise,
        },
        { headers: { "Content-Type": "application/json" } }
      );
      console.log("Config updated successfully:", updatedParams);
    } catch (error) {
      console.error("Error updating config:", error);
    }
  };


  const triggerRejectionAnalysis = async () => {
    if (!analysisParams.companyName || !analysisParams.defectType || !analysisParams.groupName) {
        alert(" Please select all required parameters before running the analysis.");
        return;
    }

    setLoading(true);
    setMessages((prev) => [
        ...prev,
        { id: Date.now(), type: "bot", content: "🔍 Running rejection analysis...", timestamp: new Date() },
    ]);

    try {

        const response = await axios.post("http://127.0.0.1:5000/analyze", {
          foundry: analysisParams.companyName,
        });

        setMessages((prev) => [
          ...prev,
          { id: Date.now(), type: "bot", content: response.data.message, timestamp: new Date() },
        ]);
        
        if (response.data.charts && Array.isArray(response.data.charts)) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now(),
              type: "bot",
              content: `📊 Showing charts for top varied parameter: **${response.data.top_parameter}**`,
              timestamp: new Date(),
            },
            {
              id: Date.now() + 1,
              type: "bot",
              content: `📅 Reference Period: **${response.data.reference_period[0]} to ${response.data.reference_period[1]}**  
        📅 Comparison Period: **${response.data.comparison_period[0]} to ${response.data.comparison_period[1]}**`,
              timestamp: new Date(),
            },
          ]);
        
          response.data.charts.forEach((url, index) => {
            setMessages((prev) => [
              ...prev,
              {
                id: Date.now() + 2 + index,
                type: "bot",
                isImage: true,
                imageUrl: url,
                timestamp: new Date(),
              },
            ]);
          });
        }
        
              
    } catch (error) {
        setMessages((prev) => [
            ...prev,
            { id: Date.now(), type: "bot", content: " Error running analysis.", timestamp: new Date() },
        ]);
    }

    setLoading(false);
};



const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognitionRef = useRef(null);
const silenceTimerRef = useRef(null);
const finalTranscriptRef = useRef("");
const isStoppingRef = useRef(false);

const handleVoiceInput = () => {
  if (!SpeechRecognition) {
    alert("Speech Recognition is not supported in this browser.");
    return;
  }

  if (!recognitionRef.current) {
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognitionRef.current = recognition;
  }

  const recognition = recognitionRef.current;

  // If already listening, stop
  if (isListening) {
    isStoppingRef.current = true;
    recognition.stop();
    setIsListening(false);
    setShowVoicePopup(false);
    clearTimeout(silenceTimerRef.current);
    return;
  }

  
  finalTranscriptRef.current = "";
  setInputMessage("");
  setIsListening(true);
  setShowVoicePopup(true);
  recognition.start();

  recognition.onresult = (event) => {
    clearTimeout(silenceTimerRef.current);
    let interimTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      const transcript = event.results[i][0].transcript.toLowerCase().trim();

      if (event.results[i].isFinal) {
        if (transcript === "clear") {
          finalTranscriptRef.current = "";
          setInputMessage("");
          return;
        }

        if (transcript === "enter") {
          recognition.stop(); // Will auto-submit in onend
          return;
        }

        finalTranscriptRef.current += transcript + " ";
      } else {
        interimTranscript += transcript;
      }
    }

    const fullTranscript = finalTranscriptRef.current + interimTranscript;
    setInputMessage(fullTranscript);

    silenceTimerRef.current = setTimeout(() => {
      recognition.stop();
      setIsListening(false);
      setShowVoicePopup(false);
    }, 5000);
  };

  recognition.onerror = (event) => {
    console.error("Speech recognition error:", event.error);
    recognition.abort();
    setIsListening(false);
    setShowVoicePopup(false);
    clearTimeout(silenceTimerRef.current);
    isStoppingRef.current = false;
  };

  recognition.onend = () => {
    isStoppingRef.current = false;
    clearTimeout(silenceTimerRef.current);
    setIsListening(false);
    setShowVoicePopup(false);

    const message = finalTranscriptRef.current.trim();
    if (message) {
      handleSendMessage();
    }
  };
};


// const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
// const recognitionRef = useRef(null);
// const silenceTimerRef = useRef(null);
// const finalTranscriptRef = useRef("");
// const isStoppingRef = useRef(false);

// const handleVoiceInput = () => {
//   if (!SpeechRecognition) {
//     alert("Speech Recognition not supported in this browser.");
//     return;
//   }

//   if (!recognitionRef.current) {
//     const recognition = new SpeechRecognition();
//     recognition.continuous = true;
//     recognition.interimResults = true;
//     recognition.lang = "en-US"; 
//     recognitionRef.current = recognition;
//   }

//   const recognition = recognitionRef.current;

//   if (isListening) {
//     isStoppingRef.current = true;
//     recognition.stop();
//     setIsListening(false);
//     setShowVoicePopup(false);
//     clearTimeout(silenceTimerRef.current);
//     return;
//   }

//   finalTranscriptRef.current = "";
//   setInputMessage("");
//   setIsListening(true);
//   setShowVoicePopup(true);
//   recognition.start();

//   recognition.onresult = (event) => {
//     clearTimeout(silenceTimerRef.current);
//     let interimTranscript = "";

//     for (let i = event.resultIndex; i < event.results.length; ++i) {
//       const transcript = event.results[i][0].transcript.toLowerCase().trim();

//       if (event.results[i].isFinal) {
//         if (transcript === "clear") {
//           finalTranscriptRef.current = "";
//           setInputMessage("");
//           return;
//         }
//         if (transcript === "enter") {
//           recognition.stop();
//           return;
//         }

//         finalTranscriptRef.current += transcript + " ";
//       } else {
//         interimTranscript += transcript;
//       }
//     }

//     const fullTranscript = finalTranscriptRef.current + interimTranscript;
//     setInputMessage(fullTranscript);

//     silenceTimerRef.current = setTimeout(() => {
//       recognition.stop();
//       setIsListening(false);
//       setShowVoicePopup(false);
//     }, 5000); 
//   };

//   recognition.onerror = (event) => {
//     console.error("Speech recognition error:", event.error);
//     recognition.abort();
//     setIsListening(false);
//     setShowVoicePopup(false);
//     clearTimeout(silenceTimerRef.current);
//     isStoppingRef.current = false;
//   };

//   recognition.onend = () => {
//     isStoppingRef.current = false;
//     clearTimeout(silenceTimerRef.current);
//     setIsListening(false);
//     setShowVoicePopup(false);

//     const finalMessage = finalTranscriptRef.current.trim();
//     if (finalMessage) {
//       handleSendMessage();
//     }
//   };
// };




const speakWithElevenLabs = async (text) => {
  try {
    const finalText = Array.isArray(text) ? text.join(" ") : text;

    const response = await fetch("http://localhost:5000/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: finalText, voice_id: "cgSgspJ2msm6clMCkdW9" }),
    });

    if (!response.ok) throw new Error("Audio generation failed");

    const blob = await response.blob();
    const audioURL = URL.createObjectURL(blob);
    const audio = new Audio(audioURL);
    audio.play();
  } catch (error) {
    console.error("ElevenLabs error:", error);
  }
};


  return (
    <div className="full-page-chatbot">
      <div className="chatbot-header enhanced-header">
  <div className="ascii-banner">
  <pre className="ascii-glow">{`
███╗   ███╗███████╗████████╗██████╗   █████╗ 
████╗ ████║██╔════╝╚══██╔══╝██╔══██╗ ██╔══██╗
██╔████╔██║█████╗     ██║   ██████╔╝ ███████║
██║╚██╔╝██║██╔══╝     ██║   ██╔══██║ ██╔══██║
██║ ╚═╝ ██║███████╗   ██║   ██║  ██║ ██║  ██║
╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═╝  ╚═╝
               M   E   T   R   A
`}</pre>


  </div>
  <button onClick={() => setIsParameterPanelOpen(!isParameterPanelOpen)} className="settings-btn">
    <Settings size={20} />
  </button>
</div>

      

      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.type === "user" ? "user-message" : "bot-message"}`}>
            {/* {message.isTable ? (
              <Table dataSource={message.tableData} columns={message.tableColumns} pagination={false} bordered />
            ) : (
              <div className="markdown-body">
                <ReactMarkdown>{message.content}</ReactMarkdown>
                {message.isImage && message.imageUrl && (
                  <div className="chart-container">
                    <img src={message.imageUrl} alt="Rejection Trend Chart" className="chart-img" />
                  </div>
                )}
              </div>
            )} */}
            {message.isTable ? (
              <Table dataSource={message.tableData} columns={message.tableColumns} pagination={false} bordered />
            ) : message.isLink ? (
              <div className="markdown-body">
                <a href={message.linkUrl} target="_blank" rel="noopener noreferrer" className="download-link">
                  📥 {message.linkText || "Download Report"}
                </a>
              </div>
            ) : (
              <div className="markdown-body">
                <ReactMarkdown>{message.content}</ReactMarkdown>
                {message.isImage && message.imageUrl && (
                  <div className="chart-container">
                    <img src={message.imageUrl} alt="Rejection Trend Chart" className="chart-img" />
                  </div>
                )}
              </div>
            )}


          </div>
        ))}
        {loading && (
            <div className="message bot-message loading-message">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div className="loading-text">Karatos is thinking...</div>
            </div>
          )}
        {isListening && <div className="message bot-message">🎙️ Listening...
          {showVoicePopup && (
          <div className="voice-popup">
            <div className="breathing-circle"></div>
            <div className="listening-text">
              <span className="wave-text">Listening</span>
            </div>
          </div>
        )}
        </div>}

        <div ref={messagesEndRef} />
        
      </div>

      <div className="chat-input">
      <button onClick={handleVoiceInput} className="mic-button">
        <img src={require("../assests/mike.png")} alt="Mic" className="mic-icon" />
      </button>

      <textarea
        className="input-box"
        value={inputMessage}
        rows={1}
        onChange={(e) => setInputMessage(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (inputMessage.trim() !== "") {
              handleSendMessage();
            }
          }
        }}
        placeholder="Ask about your defect analysis..."
      />

        <button onClick={handleSendMessage} className="send-button" disabled={inputMessage.trim() === ""}>
          <img src={require("../assests/send.ico")} alt="Send"/>
        </button>
      </div>

      {isParameterPanelOpen && (
            <div className={`parameter-panel ${isParameterPanelOpen ? "parameter-panel-open" : ""}`}>
              <h2>⚙️ Analysis Settings</h2>

              <div className="input-group">
                <label>🏭 Foundry Name</label>
                <input
                  type="text"
                  placeholder="e.g., Munjal"
                  value={analysisParams.companyName}
                  onChange={(e) =>
                    setAnalysisParams({ ...analysisParams, companyName: e.target.value })
                  }
                />
              </div>

              <div className="input-group">
                <label>🔧 Select Defect Type</label>
                <select
                  value={analysisParams.defectType}
                  onChange={(e) => handleSelectionChange("defectType", e.target.value)}
                >
                  <option value="">Select Defect</option>
                  {dropdownOptions.defectOptions.map((defect, idx) => (
                    <option key={idx} value={defect}>
                      {defect}
                    </option>
                  ))}
                </select>
              </div>

              <div className="input-group">
                <label>📊 Select Group</label>
                <select
                  value={analysisParams.groupName}
                  onChange={(e) => handleSelectionChange("groupName", e.target.value)}
                >
                  <option value="">Select Group</option>
                  {dropdownOptions.groupOptions.map((group, idx) => (
                    <option key={idx} value={group}>
                      {group}
                    </option>
                  ))}
                </select>
              </div>

              <div className="input-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={analysisParams.isComponentWise}
                    onChange={(e) =>
                      setAnalysisParams({
                        ...analysisParams,
                        isComponentWise: e.target.checked,
                      })
                    }
                    
                  />
                  Analyze Component-wise
                </label>
              </div>

              {analysisParams.isComponentWise && (
                <div className="input-group">
                  <label>🧩 Select Components</label>
                  <select
                    onChange={(e) => handleSelectionChange("components", e.target.value)}
                  >
                    <option value="">Select Component</option>
                    {dropdownOptions.componentOptions.map((comp, idx) => (
                      <option key={idx} value={comp}>
                        {comp}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <button className="run-analysis-btn" onClick={triggerRejectionAnalysis}>
                <RefreshCw size={16} style={{ marginRight: "8px" }} />
                Run Analysis
              </button>
            </div>
          )}

        <footer className="chat-footer">
          <p>📊 Built by MPM Infosoft | Powered by Fishbone Analytics</p>
        </footer>


    </div>
  );
};

export default ChatbotPage;

