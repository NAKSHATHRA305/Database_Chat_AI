import React, { useState, useEffect } from "react";
import { Plus, User, LogOut, Menu, Download, X, Trash2, Edit2, Check } from "lucide-react";
import "./Chat.css";

// Backend API URL
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

function Chat() {
  const [user, setUser] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chats, setChats] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [showExcelView, setShowExcelView] = useState(false);
  const [excelData, setExcelData] = useState(null);
  const [currentDesignId, setCurrentDesignId] = useState(null);
  const [loginForm, setLoginForm] = useState({ name: "", email: "" });
  const [isSignup, setIsSignup] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [newColumnName, setNewColumnName] = useState("");
  const [showAddColumnInput, setShowAddColumnInput] = useState(false);
  
  // Store Excel data for each design
  const [excelDataStore, setExcelDataStore] = useState({});
  
  // Chat editing
  const [editingChatId, setEditingChatId] = useState(null);
  const [editingChatTitle, setEditingChatTitle] = useState("");

  // Load user and chats from localStorage on mount
  useEffect(() => {
    const savedUser = localStorage.getItem("canopy_user");
    if (savedUser) {
      setUser(JSON.parse(savedUser));
      
      // Load chats for this user
      const savedChats = localStorage.getItem(`canopy_chats_${JSON.parse(savedUser).id}`);
      if (savedChats) {
        setChats(JSON.parse(savedChats));
      }
      
      // Load excel data store
      const savedExcelData = localStorage.getItem(`canopy_excel_${JSON.parse(savedUser).id}`);
      if (savedExcelData) {
        setExcelDataStore(JSON.parse(savedExcelData));
      }
    }
  }, []);

  // Save chats to localStorage whenever they change
  useEffect(() => {
    if (user) {
      localStorage.setItem(`canopy_chats_${user.id}`, JSON.stringify(chats));
    }
  }, [chats, user]);

  // Save excel data store whenever it changes
  useEffect(() => {
    if (user) {
      localStorage.setItem(`canopy_excel_${user.id}`, JSON.stringify(excelDataStore));
    }
  }, [excelDataStore, user]);

  // Handle Login
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const endpoint = isSignup ? "/register" : "/login";
      const payload = isSignup
        ? { name: loginForm.name, email: loginForm.email }
        : { email: loginForm.email };

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed");
      }

      // Save user to state and localStorage
      const userData = data.user;
      setUser(userData);
      localStorage.setItem("canopy_user", JSON.stringify(userData));
      
      // Load chats for this user
      const savedChats = localStorage.getItem(`canopy_chats_${userData.id}`);
      if (savedChats) {
        setChats(JSON.parse(savedChats));
      }
      
      // Load excel data for this user
      const savedExcelData = localStorage.getItem(`canopy_excel_${userData.id}`);
      if (savedExcelData) {
        setExcelDataStore(JSON.parse(savedExcelData));
      }
      
      setLoginForm({ name: "", email: "" });
      setError("");
    } catch (err) {
      setError(err.message);
      console.error("Login error:", err);
    } finally {
      setLoading(false);
    }
  };

  // Handle Logout
  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem("canopy_user");
    setShowUserMenu(false);
    setChats([]);
    setMessages([]);
    setCurrentChatId(null);
    setExcelDataStore({});
  };

  // Create New Chat
  const createNewChat = () => {
    const newChat = {
      id: Date.now(),
      title: "New Chat",
      messages: [],
    };
    setChats([newChat, ...chats]);
    setCurrentChatId(newChat.id);
    setMessages([]);
  };

  // Delete Chat
  const deleteChat = (chatId, e) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this chat?")) {
      setChats(chats.filter(chat => chat.id !== chatId));
      if (currentChatId === chatId) {
        setCurrentChatId(null);
        setMessages([]);
      }
    }
  };

  // Start Editing Chat Title
  const startEditingChat = (chatId, currentTitle, e) => {
    e.stopPropagation();
    setEditingChatId(chatId);
    setEditingChatTitle(currentTitle);
  };

  // Save Chat Title
  const saveChatTitle = (chatId) => {
    if (editingChatTitle.trim()) {
      setChats(chats.map(chat => 
        chat.id === chatId 
          ? { ...chat, title: editingChatTitle.trim() }
          : chat
      ));
    }
    setEditingChatId(null);
    setEditingChatTitle("");
  };

  // Cancel Editing
  const cancelEditing = () => {
    setEditingChatId(null);
    setEditingChatTitle("");
  };

  // Send Message and Generate Database Design
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || !user) return;

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: inputValue,
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    const prompt = inputValue;
    setInputValue("");

    // Show loading message
    const loadingMessage = {
      id: Date.now() + 1,
      role: "assistant",
      content: "🤖 Generating database design...",
      isLoading: true,
    };
    setMessages([...newMessages, loadingMessage]);

    try {
      // Call AI design endpoint
      const response = await fetch(`${API_BASE_URL}/ai/design`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt,
          user_id: user.id,
        }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.detail || "Failed to generate design");
      }

      // Store design ID for later use
      const designId = data.design_id;
      setCurrentDesignId(designId);

      // Format the response message
      const tableInfo = data.design.tables && data.design.tables.length > 0
        ? `\n\nTable: ${data.design.tables[0].table_name}\nColumns: ${data.design.tables[0].columns.map(c => c.column_name).join(", ")}`
        : "";

      // Create AI response message
      const aiResponse = {
        id: Date.now() + 2,
        role: "assistant",
        content: `✅ I've created a database design for you!\n\nDatabase: ${data.design.database_name}${tableInfo}\n\nClick below to edit it in Excel view.`,
        showExcelButton: true,
        designId: designId,
        designData: data.design,
      };

      const updatedMessages = [...newMessages, aiResponse];
      setMessages(updatedMessages);

      // Update or create chat
      if (currentChatId) {
        setChats(
          chats.map((chat) =>
            chat.id === currentChatId
              ? { ...chat, title: prompt.slice(0, 30) + "...", messages: updatedMessages }
              : chat
          )
        );
      } else {
        // Create new chat if none exists
        const newChat = {
          id: Date.now(),
          title: prompt.slice(0, 30) + "...",
          messages: updatedMessages,
        };
        setChats([newChat, ...chats]);
        setCurrentChatId(newChat.id);
      }
    } catch (err) {
      console.error("Error generating design:", err);
      const errorMessage = {
        id: Date.now() + 2,
        role: "assistant",
        content: `❌ Sorry, there was an error: ${err.message}. Please try again.`,
      };
      setMessages([...newMessages, errorMessage]);
    }
  };

  // Open Excel View with Design Data
  const openExcelView = (designData, designId) => {
    console.log("Opening Excel view with design data:", designData);
    console.log("Design ID:", designId);

    if (!designData || !designData.tables || designData.tables.length === 0) {
      alert("No table data available");
      return;
    }

    const table = designData.tables[0];
    
    // Check if we have saved data for this design
    if (excelDataStore[designId]) {
      console.log("Loading saved Excel data for design:", designId);
      setExcelData(excelDataStore[designId]);
      setCurrentDesignId(designId);
      setShowExcelView(true);
      setShowAddColumnInput(false);
      setNewColumnName("");
      return;
    }

    // Create new Excel data
    const columns = table.columns.map((col) => col.column_name);
    const rows = Array(5).fill(null).map(() => columns.map(() => ""));

    const newExcelData = {
      tableName: table.table_name,
      columns: columns,
      rows: rows,
      columnTypes: table.columns.reduce((acc, col) => {
        acc[col.column_name] = col.data_type;
        return acc;
      }, {}),
    };

    setExcelData(newExcelData);
    setCurrentDesignId(designId);
    setShowExcelView(true);
    setShowAddColumnInput(false);
    setNewColumnName("");
  };

  // Close Excel View and Save Data
  const closeExcelView = () => {
    if (currentDesignId && excelData) {
      // Save the current excel data to the store
      setExcelDataStore(prev => ({
        ...prev,
        [currentDesignId]: excelData
      }));
    }
    setShowExcelView(false);
  };

  // Handle Cell Edit
  const handleCellEdit = (rowIndex, colIndex, value) => {
    const newRows = [...excelData.rows];
    newRows[rowIndex][colIndex] = value;
    setExcelData({ ...excelData, rows: newRows });
  };

  // Add Row
  const addRow = () => {
    const newRow = excelData.columns.map(() => "");
    setExcelData({ ...excelData, rows: [...excelData.rows, newRow] });
  };

  // Add Column
  const addColumn = () => {
    if (!newColumnName.trim()) {
      alert("⚠️ Please enter a column name!");
      return;
    }

    if (excelData.columns.includes(newColumnName.trim())) {
      alert("⚠️ Column with this name already exists!");
      return;
    }

    const columnName = newColumnName.trim();
    const newColumns = [...excelData.columns, columnName];
    const newRows = excelData.rows.map(row => [...row, ""]);
    const newColumnTypes = { ...excelData.columnTypes, [columnName]: "VARCHAR(100)" };

    setExcelData({
      ...excelData,
      columns: newColumns,
      rows: newRows,
      columnTypes: newColumnTypes,
    });

    setNewColumnName("");
    setShowAddColumnInput(false);
  };

  // Download and Save Excel to PostgreSQL
  const downloadExcel = async () => {
    if (!currentDesignId) {
      alert("No design ID found. Please generate a design first.");
      return;
    }

    setLoading(true);

    try {
      const designData = excelData.rows
        .filter(row => row.some(cell => cell.trim() !== ""))
        .map((row) => {
          const rowObj = {};
          excelData.columns.forEach((col, idx) => {
            rowObj[col] = row[idx];
          });
          return rowObj;
        });

      if (designData.length === 0) {
        alert("⚠️ Please add some data before saving!");
        setLoading(false);
        return;
      }

      const response = await fetch(
        `${API_BASE_URL}/excel/${currentDesignId}/save`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: user.id,
            design_data: designData,
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Failed to save to PostgreSQL");
      }

      alert("✅ Data saved to PostgreSQL successfully!");

      const csvContent = [
        excelData.columns.join(","),
        ...excelData.rows
          .filter(row => row.some(cell => cell.trim() !== ""))
          .map((row) => row.map(cell => `"${cell}"`).join(",")),
      ].join("\n");

      const blob = new Blob([csvContent], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${excelData.tableName}_${currentDesignId}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      setTimeout(() => {
        closeExcelView();
      }, 1000);
    } catch (err) {
      console.error("Error saving Excel:", err);
      alert(`❌ Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Switch to a different chat
  const switchToChat = (chat) => {
    setCurrentChatId(chat.id);
    setMessages(chat.messages);
  };

  // --- LOGIN SCREEN ---
  if (!user) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h1 className="login-title">🗄️ Database Chat AI</h1>
          {error && (
            <div style={{ color: "red", marginBottom: "10px" }}>{error}</div>
          )}
          <form className="login-form" onSubmit={handleLogin}>
            {isSignup && (
              <>
                <label>Name</label>
                <input
                  type="text"
                  value={loginForm.name}
                  onChange={(e) =>
                    setLoginForm({ ...loginForm, name: e.target.value })
                  }
                  required
                />
              </>
            )}
            <label>Email</label>
            <input
              type="email"
              value={loginForm.email}
              onChange={(e) =>
                setLoginForm({ ...loginForm, email: e.target.value })
              }
              required
            />
            <button type="submit" className="btn primary" disabled={loading}>
              {loading ? "Loading..." : isSignup ? "Sign Up" : "Login"}
            </button>
          </form>
          <button
            onClick={() => {
              setIsSignup(!isSignup);
              setError("");
            }}
            className="link-button"
          >
            {isSignup
              ? "Already have an account? Login"
              : "Need an account? Sign Up"}
          </button>
        </div>
      </div>
    );
  }

  // --- MAIN APP ---
  return (
    <div className="app-container">
      <div className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-header">
          <h2>Chat History</h2>
          <button onClick={createNewChat} title="New Chat">
            <Plus size={20} />
          </button>
        </div>
        <div className="chat-list">
          {chats.map((chat) => (
            <div
              key={chat.id}
              className={`chat-item ${currentChatId === chat.id ? "active" : ""}`}
              onClick={() => switchToChat(chat)}
            >
              {editingChatId === chat.id ? (
                <div 
                  className="chat-edit-container"
                  onClick={(e) => e.stopPropagation()}
                >
                  <input
                    type="text"
                    value={editingChatTitle}
                    onChange={(e) => setEditingChatTitle(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === "Enter") {
                        saveChatTitle(chat.id);
                      } else if (e.key === "Escape") {
                        cancelEditing();
                      }
                    }}
                    autoFocus
                    className="chat-edit-input"
                  />
                  <button
                    onClick={() => saveChatTitle(chat.id)}
                    className="chat-action-btn"
                    title="Save"
                  >
                    <Check size={14} />
                  </button>
                  <button
                    onClick={cancelEditing}
                    className="chat-action-btn"
                    title="Cancel"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <>
                  <span className="chat-title">{chat.title}</span>
                  <div className="chat-actions">
                    <button
                      onClick={(e) => startEditingChat(chat.id, chat.title, e)}
                      className="chat-action-btn"
                      title="Rename"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      onClick={(e) => deleteChat(chat.id, e)}
                      className="chat-action-btn delete"
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="main-content">
        <div className="header">
          <button onClick={() => setSidebarOpen(!sidebarOpen)}>
            <Menu size={24} />
          </button>
          <h1>🗄️ Database Chat AI</h1>
          <div className="user-menu-container">
            <button onClick={() => setShowUserMenu(!showUserMenu)}>
              <User size={24} />
            </button>
            {showUserMenu && (
              <div className="user-dropdown">
                <div className="user-info">{user.name || user.email}</div>
                <button onClick={handleLogout} className="logout-btn">
                  <LogOut size={16} />
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <h2>Welcome, {user.name || user.email}! 👋</h2>
              <p>Start a conversation to create and manage databases</p>
              <p style={{ fontSize: "0.9rem", marginTop: "10px", opacity: 0.7 }}>
                Try: &quot;Create a products table with id, name, price&quot;
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`message ${msg.role === "user" ? "user" : "assistant"}`}
              >
                <p style={{ whiteSpace: "pre-line" }}>{msg.content}</p>
                {msg.showExcelButton && msg.designData && (
                  <button
                    className="excel-btn"
                    onClick={() => openExcelView(msg.designData, msg.designId)}
                  >
                    📊 Edit in Excel View
                  </button>
                )}
              </div>
            ))
          )}
        </div>

        <form className="input-area" onSubmit={handleSendMessage}>
          <div className="input-info">
            Logged in as: {user.name || user.email}
          </div>
          <div className="input-row">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your message... (e.g., Create a products table with id, name, price)"
            />
            <button type="submit" className="btn primary" disabled={loading}>
              {loading ? "Sending..." : "Send"}
            </button>
          </div>
        </form>
      </div>

      {showExcelView && excelData && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>Excel View - {excelData.tableName}</h2>
              <button onClick={closeExcelView}>
                <X size={24} />
              </button>
            </div>
            <div className="modal-body">
              <table>
                <thead>
                  <tr>
                    {excelData.columns.map((col, idx) => (
                      <th key={idx}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {excelData.rows.map((row, rIdx) => (
                    <tr key={rIdx}>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx}>
                          <input
                            type="text"
                            value={cell}
                            onChange={(e) =>
                              handleCellEdit(rIdx, cIdx, e.target.value)
                            }
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="modal-footer">
              <button onClick={addRow} className="btn secondary">
                + Add Row
              </button>
              
              {showAddColumnInput ? (
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <input
                    type="text"
                    value={newColumnName}
                    onChange={(e) => setNewColumnName(e.target.value)}
                    placeholder="Enter column name..."
                    style={{
                      padding: "10px 14px",
                      border: "2px solid #fce7f3",
                      borderRadius: "8px",
                      fontSize: "0.95rem"
                    }}
                    onKeyPress={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addColumn();
                      }
                    }}
                  />
                  <button onClick={addColumn} className="btn success">
                    ✓
                  </button>
                  <button 
                    onClick={() => {
                      setShowAddColumnInput(false);
                      setNewColumnName("");
                    }} 
                    className="btn secondary"
                  >
                    ✕
                  </button>
                </div>
              ) : (
                <button 
                  onClick={() => setShowAddColumnInput(true)} 
                  className="btn secondary"
                >
                  + Add Column
                </button>
              )}

              <button
                onClick={downloadExcel}
                className="btn success"
                disabled={loading}
              >
                <Download size={18} />
                {loading ? " Saving..." : " Download & Save to PostgreSQL"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Chat;