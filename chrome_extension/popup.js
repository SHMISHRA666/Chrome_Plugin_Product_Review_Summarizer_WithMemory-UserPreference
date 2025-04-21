/**
 * Popup UI script for Product Review Summariser
 * Handles UI interactions, API requests, and displaying analysis results
 */

// Wait for DOM content to load
document.addEventListener('DOMContentLoaded', () => {
  // DOM elements
  const analyzeButton = document.getElementById('analyze-button');
  const statusMessage = document.getElementById('status-message');
  const loader = document.getElementById('loader');
  const resultsContainer = document.getElementById('results-container');
  const productTitle = document.getElementById('product-title');
  const confidenceScore = document.getElementById('confidence-score');
  const confidenceLevel = document.getElementById('confidence-level');
  const sentimentScore = document.getElementById('sentiment-score');
  const sentimentText = document.getElementById('sentiment-text');
  const prosList = document.getElementById('pros-list');
  const consList = document.getElementById('cons-list');
  const reviewCount = document.getElementById('review-count');
  const warningsContainer = document.getElementById('warnings-container');
  const warningsList = document.getElementById('warnings-list');
  
  // User preferences elements
  const settingsButton = document.getElementById('settings-button');
  const preferencesContainer = document.getElementById('preferences-container');
  const preferencesForm = document.getElementById('preferences-form');
  const savePreferencesButton = document.getElementById('save-preferences');
  const cancelPreferencesButton = document.getElementById('cancel-preferences');
  
  // Form input elements
  const priceRangeMin = document.getElementById('price-range-min');
  const priceRangeMax = document.getElementById('price-range-max');
  const brandPreferences = document.getElementById('brand-preferences');
  const featurePriorities = document.getElementById('feature-priorities');
  const avoidFeatures = document.getElementById('avoid-features');
  const reviewThreshold = document.getElementById('review-threshold');
  const sentimentThreshold = document.getElementById('sentiment-threshold');
  const confidenceThreshold = document.getElementById('confidence-threshold');
  
  // Server URL will be loaded from storage in initialize()
  // Default is 'http://localhost:8080' if not found in storage
  
  // User preferences object
  let userPreferences = null;
  
  /**
   * Initialize the extension
   * Loads saved preferences and checks if current page is an Amazon product page
   */
  function initialize() {
    // Load server configuration
    chrome.storage.local.get(['serverUrl'], (result) => {
      // Get server URL from storage or use default
      let baseUrl = result.serverUrl || 'http://localhost:8080';
      
      // Sanitize the URL to remove any API endpoints
      if (baseUrl.includes('/api/')) {
        baseUrl = baseUrl.substring(0, baseUrl.indexOf('/api/'));
      }
      
      // Remove trailing slash if present
      if (baseUrl.endsWith('/')) {
        baseUrl = baseUrl.slice(0, -1);
      }
      
      window.apiUrl = baseUrl;
      console.log('Using API server URL:', window.apiUrl);
      
      // Add server URL to UI
      const serverUrlDisplay = document.createElement('div');
      serverUrlDisplay.id = 'server-url-display';
      serverUrlDisplay.className = 'server-url-display';
      serverUrlDisplay.innerHTML = `<small>Server: ${window.apiUrl} <button id="change-server-btn" class="small-btn">Change</button></small>`;
      
      // Insert at the bottom of the container
      document.querySelector('.container').appendChild(serverUrlDisplay);
      
      // Add event listener for the change server button
      document.getElementById('change-server-btn').addEventListener('click', changeServerUrl);
    });
    
    // Load saved preferences
    loadUserPreferences();
    
    // Check if current page is an Amazon product page
    checkIfProductPage();
    
    // Set up event listeners
    setupEventListeners();
  }
  
  /**
   * Set up event listeners for UI elements
   */
  function setupEventListeners() {
    // Analyze button click
    analyzeButton.addEventListener('click', startAnalysis);
    
    // Settings button click
    settingsButton.addEventListener('click', togglePreferences);
    
    // Save preferences button click
    savePreferencesButton.addEventListener('click', saveUserPreferences);
    
    // Cancel preferences button click
    cancelPreferencesButton.addEventListener('click', hidePreferences);
  }
  
  /**
   * Toggle the preferences container visibility
   */
  function togglePreferences() {
    if (preferencesContainer.classList.contains('hidden')) {
      // Show preferences and hide results
      preferencesContainer.classList.remove('hidden');
      resultsContainer.classList.add('hidden');
      
      // Populate form with current preferences
      populatePreferencesForm();
    } else {
      // Hide preferences
      hidePreferences();
    }
  }
  
  /**
   * Hide the preferences container
   */
  function hidePreferences() {
    preferencesContainer.classList.add('hidden');
  }
  
  /**
   * Load user preferences from chrome.storage
   */
  function loadUserPreferences() {
    chrome.storage.local.get(['userPreferences'], (result) => {
      if (result.userPreferences) {
        userPreferences = result.userPreferences;
        console.log('Loaded user preferences:', userPreferences);
      } else {
        // Set default preferences
        userPreferences = {
          price_range: { min: 0, max: 0 },
          brand_preferences: [],
          feature_priorities: [],
          avoid_features: [],
          review_threshold: 10,
          sentiment_threshold: 0.5,
          confidence_threshold: 70
        };
        console.log('Using default preferences');
      }
    });
  }
  
  /**
   * Populate the preferences form with current values
   */
  function populatePreferencesForm() {
    if (!userPreferences) return;
    
    // Set price range
    priceRangeMin.value = userPreferences.price_range.min || 0;
    priceRangeMax.value = userPreferences.price_range.max || 0;
    
    // Set brand preferences
    brandPreferences.value = userPreferences.brand_preferences.join(', ');
    
    // Set feature priorities
    featurePriorities.value = userPreferences.feature_priorities.join(', ');
    
    // Set features to avoid
    avoidFeatures.value = userPreferences.avoid_features.join(', ');
    
    // Set thresholds
    reviewThreshold.value = userPreferences.review_threshold || 10;
    sentimentThreshold.value = userPreferences.sentiment_threshold || 0.5;
    confidenceThreshold.value = userPreferences.confidence_threshold || 70;
  }
  
  /**
   * Save user preferences to chrome.storage
   */
  function saveUserPreferences() {
    // Create preferences object from form values
    const newPreferences = {
      price_range: {
        min: parseFloat(priceRangeMin.value) || 0,
        max: parseFloat(priceRangeMax.value) || 0
      },
      brand_preferences: brandPreferences.value.split(',').map(brand => brand.trim()).filter(brand => brand),
      feature_priorities: featurePriorities.value.split(',').map(feature => feature.trim()).filter(feature => feature),
      avoid_features: avoidFeatures.value.split(',').map(feature => feature.trim()).filter(feature => feature),
      review_threshold: parseInt(reviewThreshold.value) || 10,
      sentiment_threshold: parseFloat(sentimentThreshold.value) || 0.5,
      confidence_threshold: parseInt(confidenceThreshold.value) || 70
    };
    
    // Save to chrome.storage
    chrome.storage.local.set({ userPreferences: newPreferences }, () => {
      userPreferences = newPreferences;
      console.log('Saved user preferences:', userPreferences);
      
      // Hide preferences form
      hidePreferences();
      
      // Show success message
      statusMessage.textContent = 'Preferences saved successfully';
      statusMessage.className = 'status-info';
      
      // Reset message after 3 seconds
      setTimeout(() => {
        if (analyzeButton.disabled) {
          statusMessage.textContent = 'Ready to analyze Amazon product reviews';
        }
      }, 3000);
    });
  }
  
  /**
   * Check if current page is an Amazon product page and verify content script status
   * Enables or disables the analyze button based on the result
   */
  function checkIfProductPage() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || tabs.length === 0) {
        disableAnalysis('Cannot detect current tab');
        return;
      }
      
      const currentUrl = tabs[0].url;
      console.log("Current URL:", currentUrl);
      
      // More comprehensive Amazon product page detection
      const isAmazonProduct = /amazon\.(com|co\.uk|ca|de|fr|es|it|nl|in|co\.jp|com\.au).*\/(dp|gp\/product|product-reviews)\/[A-Z0-9]{10}/i.test(currentUrl);
      
      if (isAmazonProduct) {
        console.log("Amazon product detected");
        // Check if content script is loaded
        ensureContentScriptLoaded(tabs[0].id, () => {
          enableAnalysis();
        }, () => {
          disableAnalysis('Content script could not be loaded. Try refreshing the page.');
        });
      } else {
        console.log("Not an Amazon product page");
        disableAnalysis('Navigate to an Amazon product page to analyze reviews');
      }
    });
  }
  
  /**
   * Ensure content script is loaded in the active tab
   * Attempts to inject the content script if not already loaded
   * 
   * @param {number} tabId - ID of the active tab
   * @param {Function} onSuccess - Callback when content script is loaded
   * @param {Function} onFailure - Callback when content script fails to load
   */
  function ensureContentScriptLoaded(tabId, onSuccess, onFailure) {
    // First try to ping the content script
    chrome.tabs.sendMessage(tabId, { action: 'ping' }, response => {
      if (chrome.runtime.lastError || !response) {
        console.log("Content script not detected, attempting to inject it");
        
        // Script isn't loaded, try to inject it
        chrome.scripting.executeScript({
          target: { tabId: tabId },
          files: ['content.js']
        }).then(() => {
          console.log("Content script injection successful");
          
          // Give it a moment to initialize
          setTimeout(() => {
            // Verify injection worked
            chrome.tabs.sendMessage(tabId, { action: 'ping' }, verifyResponse => {
              if (chrome.runtime.lastError || !verifyResponse) {
                console.error("Content script still not responding after injection");
                onFailure();
              } else {
                console.log("Content script now responding");
                onSuccess();
              }
            });
          }, 200);
        }).catch(error => {
          console.error("Failed to inject content script:", error);
          onFailure();
        });
      } else {
        console.log("Content script already loaded");
        onSuccess();
      }
    });
  }
  
  /**
   * Enable the analyze button with a ready status message
   */
  function enableAnalysis() {
    statusMessage.textContent = 'Ready to analyze Amazon product reviews';
    statusMessage.className = 'status-info';
    analyzeButton.disabled = false;
  }
  
  /**
   * Disable the analyze button with a custom message
   * @param {string} message - Message to display to the user
   */
  function disableAnalysis(message) {
    statusMessage.textContent = message;
    statusMessage.className = 'status-warning';
    analyzeButton.disabled = true;
    hideResults();
  }
  
  /**
   * Show loading state while waiting for analysis results
   */
  function showLoading() {
    analyzeButton.disabled = true;
    loader.classList.remove('hidden');
    statusMessage.textContent = 'Analyzing product reviews...';
    statusMessage.className = 'status-info';
    hideResults();
  }
  
  /**
   * Show error state with a custom message
   * @param {string} message - Error message to display to the user
   */
  function showError(message) {
    statusMessage.textContent = message;
    statusMessage.className = 'status-error';
    loader.classList.add('hidden');
    analyzeButton.disabled = false;
    hideResults();
  }
  
  /**
   * Hide the results container
   */
  function hideResults() {
    resultsContainer.classList.add('hidden');
  }
  
  /**
   * Start the product analysis process
   * Requests product data from content script and sends it to API server
   */
  function startAnalysis() {
    showLoading();

    // Check if the API URL is loaded
    if (!window.apiUrl) {
      showError('Server URL not loaded yet. Please try again in a moment.');
      return;
    }

    // First check if the server is running
    checkServerConnection()
      .then(isConnected => {
        if (!isConnected) {
          throw new Error(`Cannot connect to server at ${window.apiUrl}`);
        }
        
        // Continue with the analysis process
        return chrome.tabs.query({ active: true, currentWindow: true });
      })
      .then(tabs => {
        if (!tabs || tabs.length === 0) {
          throw new Error('Cannot detect current tab');
        }
        
        // Now that we know the content script is loaded, send the scrape request
        return new Promise((resolve, reject) => {
          ensureContentScriptLoaded(tabs[0].id, () => {
            chrome.tabs.sendMessage(
              tabs[0].id,
              { action: 'scrapeProductData' },
              (response) => {
                // Handle any communication errors
                if (chrome.runtime.lastError) {
                  console.error("Runtime error:", chrome.runtime.lastError);
                  reject(new Error(chrome.runtime.lastError.message));
                  return;
                }
                
                // Check for valid response
                if (!response || !response.productData) {
                  reject(new Error('Failed to retrieve product data'));
                  return;
                }
                
                // If there's a warning in the response
                if (response.warning) {
                  statusMessage.textContent = response.warning;
                  statusMessage.className = 'status-warning';
                }
                
                // Add user preferences to the product data
                if (userPreferences) {
                  response.productData.user_preferences = userPreferences;
                }
                
                resolve(response.productData);
              }
            );
          }, () => {
            reject(new Error('Could not communicate with the page. Try refreshing the page and try again.'));
          });
        });
      })
      .then(productData => {
        // Send product data to API server
        sendToApiServer(productData);
      })
      .catch(error => {
        console.error('Analysis error:', error);
        showError(error.message);
        loader.classList.add('hidden');
        analyzeButton.disabled = false;
      });
  }
  
  /**
   * Check if the server is running by making a simple GET request
   * @returns {Promise<boolean>} Promise that resolves to true if server is running
   */
  function checkServerConnection() {
    // Make sure the API URL doesn't include any endpoints
    let baseUrl = window.apiUrl;
    
    // Remove common API endpoints if they exist in the URL
    if (baseUrl.includes('/api/')) {
      baseUrl = baseUrl.substring(0, baseUrl.indexOf('/api/'));
    }
    
    const healthUrl = `${baseUrl}/`;
    console.log('Checking server health at:', healthUrl);
    
    return fetch(healthUrl, { 
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    })
    .then(response => {
      return response.ok;
    })
    .catch(error => {
      console.error('Server connection check failed:', error);
      return false;
    });
  }
  
  /**
   * Handle memory match response from the API
   * @param {Object} data - API response with memory match data
   * @param {Object} productData - Original product data
   */
  function handleMemoryMatch(data, productData) {
    console.log("Memory match found:", data);
    
    // Create a modal dialog
    const modalOverlay = document.createElement('div');
    modalOverlay.className = 'modal-overlay';
    
    const modalContainer = document.createElement('div');
    modalContainer.className = 'modal-container';
    
    const modalHeader = document.createElement('div');
    modalHeader.className = 'modal-header';
    modalHeader.innerHTML = '<h3>Existing Analysis Found</h3>';
    
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    
    // Format timestamp if available
    let timestampText = '';
    if (data.existing_analysis && data.existing_analysis.timestamp) {
      try {
        const timestamp = new Date(data.existing_analysis.timestamp);
        timestampText = ` (from ${timestamp.toLocaleDateString()})`;
      } catch (e) {
        console.error('Error formatting timestamp:', e);
      }
    }
    
    // Prepare the modal content - include summary only if available
    let modalHtml = `<p>We found an existing analysis for this product${timestampText}.</p>`;
    
    // Only add the summary line if a non-empty summary exists
    if (data.existing_analysis && data.existing_analysis.summary && 
        data.existing_analysis.summary !== 'No summary available' && 
        data.existing_analysis.summary.trim() !== '') {
      modalHtml += `<p>Summary: ${data.existing_analysis.summary}</p>`;
    }
    
    modalHtml += `<p>Would you like to use the existing analysis or perform a new one?</p>`;
    
    modalContent.innerHTML = modalHtml;
    
    const modalFooter = document.createElement('div');
    modalFooter.className = 'modal-footer';
    
    const useExistingBtn = document.createElement('button');
    useExistingBtn.className = 'btn btn-primary';
    useExistingBtn.textContent = 'Use Existing';
    
    const newAnalysisBtn = document.createElement('button');
    newAnalysisBtn.className = 'btn btn-secondary';
    newAnalysisBtn.textContent = 'New Analysis';
    
    // Add buttons to footer
    modalFooter.appendChild(useExistingBtn);
    modalFooter.appendChild(newAnalysisBtn);
    
    // Build modal structure
    modalContainer.appendChild(modalHeader);
    modalContainer.appendChild(modalContent);
    modalContainer.appendChild(modalFooter);
    modalOverlay.appendChild(modalContainer);
    
    // Add modal to the popup
    document.body.appendChild(modalOverlay);
    
    // Handle button clicks
    useExistingBtn.addEventListener('click', async () => {
      // Remove the modal
      document.body.removeChild(modalOverlay);
      
      // Show loading
      showLoading();
      
      try {
        // Call the memory choice API endpoint
        // Make sure the API URL doesn't already include the endpoint
        const baseUrl = window.apiUrl.endsWith('/api/handle-memory-choice') ? 
          window.apiUrl.replace('/api/handle-memory-choice', '') : 
          window.apiUrl;
        
        const memoryApiUrl = `${baseUrl}/api/handle-memory-choice`;
        console.log('Sending memory choice to API:', memoryApiUrl);
        
        // Prepare the request payload
        const requestData = {
          choice: 'use_existing',
          product_id: data.existing_analysis.product_id
        };
        
        console.log('Sending use_existing request with data:', requestData);
        
        const response = await fetch(memoryApiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify(requestData)
        });
        
        // Log full response details
        console.log('Response status:', response.status, response.statusText);
        const responseText = await response.text();
        
        try {
          // Try to parse as JSON
          const responseData = JSON.parse(responseText);
          console.log('Response data:', responseData);
          
          if (!response.ok) {
            console.error(`Memory API error: ${response.status} ${response.statusText}`, responseData);
            
            // If there's a specific error message in the response, show it
            if (responseData && responseData.error) {
              throw new Error(responseData.error);
            } else {
              throw new Error(`Server returned ${response.status} ${response.statusText}`);
            }
          }
          
          // Process and display the result
          chrome.runtime.sendMessage(
            { action: 'processApiResults', data: responseData },
            (processedResponse) => {
              if (processedResponse && processedResponse.status === 'success') {
                displayResults(processedResponse.processedData, productData.title);
                statusMessage.textContent = 'Retrieved analysis from memory!';
                statusMessage.className = 'status-success';
              } else {
                showError('Error processing API results');
              }
            }
          );
        } catch (jsonError) {
          // Handle non-JSON responses
          console.error('Failed to parse response as JSON:', jsonError);
          console.log('Raw response:', responseText);
          
          if (!response.ok) {
            throw new Error(`Server returned ${response.status} ${response.statusText} - Not a valid JSON response`);
          }
          
          showError('Server returned an invalid response format');
        }
      } catch (error) {
        console.error('Memory choice API error:', error);
        if (error.message.includes('Failed to fetch')) {
          showError(`Server connection error: Please ensure the API server is running at ${window.apiUrl}`);
        } else {
          showError(`Server error: ${error.message}`);
        }
      } finally {
        loader.classList.add('hidden');
        analyzeButton.disabled = false;
      }
    });
    
    newAnalysisBtn.addEventListener('click', async () => {
      // Remove the modal
      document.body.removeChild(modalOverlay);
      
      // Show loading
      showLoading();
      
      try {
        // Call the memory choice API endpoint
        // Make sure the API URL doesn't already include the endpoint
        const baseUrl = window.apiUrl.endsWith('/api/handle-memory-choice') ? 
          window.apiUrl.replace('/api/handle-memory-choice', '') : 
          window.apiUrl;
        
        const memoryApiUrl = `${baseUrl}/api/handle-memory-choice`;
        console.log('Sending memory choice to API:', memoryApiUrl);
        
        // Ensure productData has the required fields
        const cleanProductData = {
          title: productData.title || '',
          site: productData.site || 'amazon.com',
          url: productData.url || window.location.href,
          price: productData.price || '',
          reviews: Array.isArray(productData.reviews) ? productData.reviews : [],
          force_new_analysis: true
        };
        
        // Add user preferences if available
        if (userPreferences) {
          cleanProductData.user_preferences = userPreferences;
        }
        
        console.log('Sending new analysis request with data:', cleanProductData);
        
        const response = await fetch(memoryApiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            choice: 'new_analysis',
            product_data: cleanProductData
          })
        });
        
        // Log full response details
        console.log('Response status:', response.status, response.statusText);
        const responseText = await response.text();
        
        try {
          // Try to parse as JSON
          const responseData = JSON.parse(responseText);
          console.log('Response data:', responseData);
          
          if (!response.ok) {
            console.error(`Memory API error: ${response.status} ${response.statusText}`, responseData);
            
            // If there's a specific error message in the response, show it
            if (responseData && responseData.error) {
              throw new Error(responseData.error);
            } else {
              throw new Error(`Server returned ${response.status} ${response.statusText}`);
            }
          }
          
          // Process and display the result
          chrome.runtime.sendMessage(
            { action: 'processApiResults', data: responseData },
            (processedResponse) => {
              if (processedResponse && processedResponse.status === 'success') {
                displayResults(processedResponse.processedData, productData.title);
                statusMessage.textContent = 'Analysis complete!';
                statusMessage.className = 'status-success';
              } else {
                showError('Error processing API results');
              }
            }
          );
        } catch (jsonError) {
          // Handle non-JSON responses
          console.error('Failed to parse response as JSON:', jsonError);
          console.log('Raw response:', responseText);
          
          if (!response.ok) {
            throw new Error(`Server returned ${response.status} ${response.statusText} - Not a valid JSON response`);
          }
          
          showError('Server returned an invalid response format');
        }
      } catch (error) {
        console.error('Memory choice API error:', error);
        if (error.message.includes('Failed to fetch')) {
          showError(`Server connection error: Please ensure the API server is running at ${window.apiUrl}`);
        } else {
          showError(`Server error: ${error.message}`);
        }
      } finally {
        loader.classList.add('hidden');
        analyzeButton.disabled = false;
      }
    });
  }
  
  /**
   * Send product data to the API server for analysis
   * @param {Object} productData - Product data object to analyze
   */
  function sendToApiServer(productData) {
    // Make sure the API URL doesn't already include the endpoint
    const baseUrl = window.apiUrl.endsWith('/api/detect-product') ? 
      window.apiUrl.replace('/api/detect-product', '') : 
      window.apiUrl;
      
    const apiUrl = `${baseUrl}/api/detect-product`;
    console.log('Sending to API:', productData);
    console.log('API URL:', apiUrl);
    
    // Show loading indicator
    showLoading();
    
    // Make sure we have the title and site for the API
    if (!productData.title || productData.title.trim() === '') {
      productData.title = document.title || 'Unknown Product';
    }
    
    // Make sure site is set
    if (!productData.site || productData.site.trim() === '') {
      productData.site = 'amazon.com';
    }
    
    // Always request full details to avoid hidden pros/cons
    productData.include_full_details = true;
    
    console.log('Attempting to connect to API at:', apiUrl);

    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(productData)
    })
    .then(response => {
      if (!response.ok) {
        console.error(`Server response not OK: ${response.status} ${response.statusText}`);
        throw new Error(`Server returned ${response.status} ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      // Check if this is a memory match response
      if (data.status === 'memory_match_found') {
        // Handle memory match
        loader.classList.add('hidden');
        analyzeButton.disabled = false;
        handleMemoryMatch(data, productData);
        return;
      }
      
      // Process data through background script (to handle hidden fields)
      chrome.runtime.sendMessage(
        { action: 'processApiResults', data: data },
        (processedResponse) => {
          if (processedResponse && processedResponse.status === 'success') {
            // Show results in the popup
            displayResults(processedResponse.processedData, productData.title);
            
            // If we need a refresh, show a warning
            if (processedResponse.needsRefresh) {
              statusMessage.textContent = "Some details are hidden. Click 'Analyze Reviews' again for full details.";
              statusMessage.className = 'status-warning';
            } else {
              statusMessage.textContent = 'Analysis complete!';
              statusMessage.className = 'status-success';
            }
          } else {
            showError('Error processing API results');
          }
        }
      );
    })
    .catch(error => {
      console.error('API error details:', error);
      
      // Check if it's a network error
      if (error.message.includes('Failed to fetch')) {
        showError(`Server connection error: Please ensure the API server is running at ${window.apiUrl}`);
      } else {
        showError(`Server error: ${error.message}`);
      }
    })
    .finally(() => {
      loader.classList.add('hidden');
      analyzeButton.disabled = false;
    });
  }
  
  /**
   * Display analysis results in the popup UI
   * @param {Object} data - API response data with sentiment analysis and confidence scores
   * @param {string} title - Product title
   */
  function displayResults(data, title) {
    console.log("Displaying results:", data);
    
    // Make sure the results container is visible
    resultsContainer.classList.remove('hidden');
    
    // Display product title
    productTitle.textContent = title;
    
    // Display confidence score
    const confidenceVal = data.confidence_score || 0;
    confidenceScore.textContent = `${Math.round(confidenceVal)}%`;
    confidenceScore.style.color = getConfidenceColor(confidenceVal);
    confidenceLevel.textContent = data.confidence_level || 'Unknown';
    
    // Display sentiment score
    const sentimentVal = data.sentiment_score || 0;
    sentimentScore.textContent = sentimentVal.toFixed(2);
    sentimentScore.style.color = getSentimentColor(sentimentVal);
    sentimentText.textContent = data.overall_sentiment || 'Unknown';
    
    /**
     * Sanitize and escape text to prevent XSS vulnerabilities
     * @param {string} text - Input text to sanitize
     * @returns {string} Sanitized text safe for display
     */
    function sanitizeText(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
    
    // Display pros
    prosList.innerHTML = '';
    if (data.pros && data.pros.length > 0) {
      data.pros.forEach(pro => {
        const li = document.createElement('li');
        li.innerHTML = sanitizeText(pro);
        prosList.appendChild(li);
      });
    } else {
      const li = document.createElement('li');
      li.textContent = 'No pros identified';
      li.className = 'no-items';
      prosList.appendChild(li);
    }
    
    // Display cons
    consList.innerHTML = '';
    if (data.cons && data.cons.length > 0) {
      data.cons.forEach(con => {
        const li = document.createElement('li');
        li.innerHTML = sanitizeText(con);
        consList.appendChild(li);
      });
    } else {
      const li = document.createElement('li');
      li.textContent = 'No cons identified';
      li.className = 'no-items';
      consList.appendChild(li);
    }
    
    // Display review count
    reviewCount.textContent = data.review_count || 0;
    
    // Display warnings if any
    if (data.warnings && data.warnings.length > 0) {
      warningsContainer.classList.remove('hidden');
      warningsList.innerHTML = '';
      data.warnings.forEach(warning => {
        const li = document.createElement('li');
        li.textContent = warning;
        warningsList.appendChild(li);
      });
    } else {
      warningsContainer.classList.add('hidden');
    }
    
    // Display preference matching if available
    if (data.preference_match_score !== undefined && data.preference_match_score !== null) {
        // Create preference match container if it doesn't exist
        let preferenceContainer = document.getElementById('preference-container');
        if (!preferenceContainer) {
            preferenceContainer = document.createElement('div');
            preferenceContainer.id = 'preference-container';
            preferenceContainer.className = 'preference-container';
            
            const heading = document.createElement('h3');
            heading.textContent = 'Preference Match';
            preferenceContainer.appendChild(heading);
            
            const scoreBox = document.createElement('div');
            scoreBox.className = 'score-circle';
            scoreBox.id = 'preference-score';
            preferenceContainer.appendChild(scoreBox);
            
            // Add preference match analysis paragraph
            const analysisBox = document.createElement('div');
            analysisBox.className = 'preference-analysis';
            analysisBox.id = 'preference-analysis';
            preferenceContainer.appendChild(analysisBox);
            
            const matchesList = document.createElement('ul');
            matchesList.id = 'matches-list';
            preferenceContainer.appendChild(matchesList);
            
            const mismatchesList = document.createElement('ul');
            mismatchesList.id = 'mismatches-list';
            preferenceContainer.appendChild(mismatchesList);
            
            // Insert after pros-cons-container
            const prosConsContainer = document.querySelector('.pros-cons-container');
            prosConsContainer.parentNode.insertBefore(preferenceContainer, prosConsContainer.nextSibling);
        }
        
        // Update preference match score
        const preferenceScore = document.getElementById('preference-score');
        preferenceScore.textContent = `${data.preference_match_score}%`;
        
        // Set color based on score
        if (data.preference_match_score >= 80) {
            preferenceScore.style.backgroundColor = '#27ae60'; // Green
        } else if (data.preference_match_score >= 50) {
            preferenceScore.style.backgroundColor = '#f39c12'; // Orange
        } else {
            preferenceScore.style.backgroundColor = '#e74c3c'; // Red
        }
        
        // Update preference match analysis if available
        const preferenceAnalysis = document.getElementById('preference-analysis');
        if (data.preference_match_analysis) {
            preferenceAnalysis.textContent = data.preference_match_analysis;
            preferenceAnalysis.classList.remove('hidden');
        } else {
            preferenceAnalysis.classList.add('hidden');
        }
        
        // Display matches
        const matchesList = document.getElementById('matches-list');
        matchesList.innerHTML = '<h4>Matches</h4>';
        if (data.preference_matches && Object.keys(data.preference_matches).length > 0) {
            for (const [key, value] of Object.entries(data.preference_matches)) {
                const li = document.createElement('li');
                li.textContent = value;
                li.className = 'match-item';
                matchesList.appendChild(li);
            }
        } else {
            const li = document.createElement('li');
            li.textContent = 'No preference matches found';
            li.className = 'no-matches';
            matchesList.appendChild(li);
        }
        
        // Display mismatches
        const mismatchesList = document.getElementById('mismatches-list');
        mismatchesList.innerHTML = '<h4>Mismatches</h4>';
        if (data.preference_mismatches && Object.keys(data.preference_mismatches).length > 0) {
            for (const [key, value] of Object.entries(data.preference_mismatches)) {
                const li = document.createElement('li');
                li.textContent = value;
                li.className = 'mismatch-item';
                mismatchesList.appendChild(li);
            }
        } else {
            const li = document.createElement('li');
            li.textContent = 'No preference mismatches found';
            li.className = 'no-mismatches';
            mismatchesList.appendChild(li);
        }
    }
  }
  
  /**
   * Get a color corresponding to a confidence score value
   * @param {number} score - Confidence score (0-100)
   * @returns {string} CSS color value
   */
  function getConfidenceColor(score) {
    if (score >= 70) return '#27ae60'; // Green for high confidence
    if (score >= 40) return '#f39c12'; // Orange for medium confidence
    return '#e74c3c'; // Red for low confidence
  }
  
  /**
   * Get a color corresponding to a sentiment score value
   * @param {number} score - Sentiment score (-1 to 1)
   * @returns {string} CSS color value
   */
  function getSentimentColor(score) {
    if (score >= 0.3) return '#27ae60';  // Green for positive
    if (score <= -0.3) return '#e74c3c'; // Red for negative
    return '#f39c12'; // Orange for neutral
  }
  
  /**
   * Show dialog to change server URL
   */
  function changeServerUrl() {
    const currentUrl = window.apiUrl;
    
    const newUrl = prompt('Enter server URL (e.g., http://localhost:8080)', currentUrl);
    
    if (newUrl && newUrl !== currentUrl) {
      // Sanitize the URL to remove any API endpoints
      let sanitizedUrl = newUrl;
      
      // Remove common API endpoints if they exist in the URL
      if (sanitizedUrl.includes('/api/')) {
        sanitizedUrl = sanitizedUrl.substring(0, sanitizedUrl.indexOf('/api/'));
      }
      
      // Remove trailing slash if present
      if (sanitizedUrl.endsWith('/')) {
        sanitizedUrl = sanitizedUrl.slice(0, -1);
      }
      
      // Store the sanitized URL
      chrome.storage.local.set({ serverUrl: sanitizedUrl }, () => {
        window.apiUrl = sanitizedUrl;
        console.log('Server URL updated to:', sanitizedUrl);
        
        // Update the display
        const display = document.getElementById('server-url-display');
        if (display) {
          display.innerHTML = `<small>Server: ${sanitizedUrl} <button id="change-server-btn" class="small-btn">Change</button></small>`;
          document.getElementById('change-server-btn').addEventListener('click', changeServerUrl);
        }
        
        // Show success message
        statusMessage.textContent = 'Server URL updated. Please try your request again.';
        statusMessage.className = 'status-info';
      });
    }
  }
  
  // Initialize the extension
  initialize();
}); 