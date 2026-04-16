// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

contract ChainOfCustody {

    // Enum for action types
    enum Action { COLLECTED, TRANSFERRED, ANALYZED, VERIFIED, ARCHIVED }

    // Struct for each custody event
    struct CustodyEvent {
        uint256 evidenceId;
        string fileHash;       // SHA-256 hash of the file
        string fileName;
        Action action;
        string actor;          // name/address of person performing action
        string notes;
        uint256 timestamp;
    }

    // Struct to hold evidence metadata
    struct Evidence {
        uint256 id;
        string fileHash;
        string fileName;
        string fileType;
        uint256 fileSize;
        string uploadedBy;
        uint256 createdAt;
        bool exists;
        bool isEncrypted;
        uint256 eventCount;
    }

    // Storage
    mapping(uint256 => Evidence) public evidences;
    mapping(uint256 => CustodyEvent[]) public custodyChain;
    uint256 public evidenceCounter;

    // Events
    event EvidenceAdded(uint256 indexed evidenceId, string fileHash, string uploadedBy, uint256 timestamp);
    event CustodyUpdated(uint256 indexed evidenceId, Action action, string actor, uint256 timestamp);

    // Add new evidence to blockchain
    function addEvidence(
        string memory _fileHash,
        string memory _fileName,
        string memory _fileType,
        uint256 _fileSize,
        string memory _uploadedBy,
        bool _isEncrypted
    ) public returns (uint256) {
        evidenceCounter++;
        uint256 newId = evidenceCounter;

        evidences[newId] = Evidence({
            id: newId,
            fileHash: _fileHash,
            fileName: _fileName,
            fileType: _fileType,
            fileSize: _fileSize,
            uploadedBy: _uploadedBy,
            createdAt: block.timestamp,
            exists: true,
            isEncrypted: _isEncrypted,
            eventCount: 1
        });

        // Log initial collection event
        custodyChain[newId].push(CustodyEvent({
            evidenceId: newId,
            fileHash: _fileHash,
            fileName: _fileName,
            action: Action.COLLECTED,
            actor: _uploadedBy,
            notes: "Evidence initially collected and recorded on blockchain",
            timestamp: block.timestamp
        }));

        emit EvidenceAdded(newId, _fileHash, _uploadedBy, block.timestamp);
        return newId;
    }

    // Log a custody action (transfer, analyze, archive, etc.)
    function logCustodyEvent(
        uint256 _evidenceId,
        string memory _fileHash,
        uint8 _action,
        string memory _actor,
        string memory _notes
    ) public {
        require(evidences[_evidenceId].exists, "Evidence does not exist");

        custodyChain[_evidenceId].push(CustodyEvent({
            evidenceId: _evidenceId,
            fileHash: _fileHash,
            fileName: evidences[_evidenceId].fileName,
            action: Action(_action),
            actor: _actor,
            notes: _notes,
            timestamp: block.timestamp
        }));

        evidences[_evidenceId].eventCount++;
        emit CustodyUpdated(_evidenceId, Action(_action), _actor, block.timestamp);
    }

    // Verify evidence integrity - returns (isAuthentic, storedHash)
    function verifyEvidence(uint256 _evidenceId, string memory _newHash)
        public view returns (bool isAuthentic, string memory storedHash)
    {
        require(evidences[_evidenceId].exists, "Evidence does not exist");
        storedHash = evidences[_evidenceId].fileHash;
        isAuthentic = (keccak256(bytes(storedHash)) == keccak256(bytes(_newHash)));
    }

    // Get all custody events for an evidence item
    function getCustodyChain(uint256 _evidenceId)
        public view returns (CustodyEvent[] memory)
    {
        require(evidences[_evidenceId].exists, "Evidence does not exist");
        return custodyChain[_evidenceId];
    }

    // Get total number of evidence items
    function getEvidenceCount() public view returns (uint256) {
        return evidenceCounter;
    }

    // Get evidence metadata
    function getEvidence(uint256 _evidenceId)
        public view returns (Evidence memory)
    {
        require(evidences[_evidenceId].exists, "Evidence does not exist");
        return evidences[_evidenceId];
    }

    // Get all evidence IDs (for listing)
    function getAllEvidenceIds() public view returns (uint256[] memory) {
        uint256[] memory ids = new uint256[](evidenceCounter);
        for (uint256 i = 1; i <= evidenceCounter; i++) {
            ids[i - 1] = i;
        }
        return ids;
    }
}
