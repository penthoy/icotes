"""
Integration tests for File System Service

Tests file operations, directory management, file watching, search functionality,
and event publishing with comprehensive error handling and edge cases.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import json

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.services.filesystem_service import (
    FileSystemService, FileInfo, FileType, FilePermission, SearchResult,
    get_filesystem_service, shutdown_filesystem_service
)
from icpy.core.message_broker import get_message_broker, shutdown_message_broker
from icpy.core.connection_manager import get_connection_manager, shutdown_connection_manager


class TestFileSystemService:
    """Test suite forFileSystemService"""
    
    @pytest_asyncio.fixture
    async def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest_asyncio.fixture
    async def filesystem_service(self, temp_dir):
        """Create a fresh filesystem service for each test"""
        # Reset global instances
        try:
            await shutdown_filesystem_service()
        except RuntimeError:
            pass  # Event loop may already be closed
        try:
            await shutdown_message_broker()
        except RuntimeError:
            pass  # Event loop may already be closed
        try:
            await shutdown_connection_manager()
        except RuntimeError:
            pass  # Event loop may already be closed
        
        # Initialize message broker and connection manager
        from icpy.core.message_broker import get_message_broker
        from icpy.core.connection_manager import get_connection_manager
        
        message_broker = await get_message_broker()
        await message_broker.start()
        
        connection_manager = await get_connection_manager()
        await connection_manager.start()
        
        service = FileSystemService(root_path=temp_dir)
        await service.initialize()
        
        yield service
        
        # Cleanup
        try:
            await service.shutdown()
        except RuntimeError:
            pass  # Event loop may already be closed
        try:
            await shutdown_filesystem_service()
        except RuntimeError:
            pass  # Event loop may already be closed
    
    @pytest_asyncio.fixture
    async def sample_files(self, temp_dir, filesystem_service):
        """Create sample files for testing"""
        files = {}
        
        # Create test files
        files['test.txt'] = os.path.join(temp_dir, 'test.txt')
        with open(files['test.txt'], 'w') as f:
            f.write("Hello World\nThis is a test file\nWith multiple lines")
        
        files['script.py'] = os.path.join(temp_dir, 'script.py')
        with open(files['script.py'], 'w') as f:
            f.write("#!/usr/bin/env python3\nprint('Hello from Python')\n")
        
        files['data.json'] = os.path.join(temp_dir, 'data.json')
        with open(files['data.json'], 'w') as f:
            json.dump({"key": "value", "number": 42}, f)
        
        # Create subdirectory with files
        subdir = os.path.join(temp_dir, 'subdir')
        os.makedirs(subdir)
        files['subdir'] = subdir
        
        files['sub_file.md'] = os.path.join(subdir, 'README.md')
        with open(files['sub_file.md'], 'w') as f:
            f.write("# README\n\nThis is a markdown file in a subdirectory")
        
        # Create hidden file
        files['hidden'] = os.path.join(temp_dir, '.hidden')
        with open(files['hidden'], 'w') as f:
            f.write("Hidden file content")
        
        # Rebuild the index after creating files
        await filesystem_service.rebuild_index()
        
        return files

    @pytest.mark.asyncio
    async def test_service_initialization(self, filesystem_service, temp_dir):
        """Test filesystem service initialization"""
        assert filesystem_service is not None
        assert filesystem_service.root_path == temp_dir
        assert filesystem_service.message_broker is not None
        assert filesystem_service.connection_manager is not None
        assert filesystem_service.observer is not None
        assert len(filesystem_service.watched_paths) > 0
        
        # Check statistics
        stats = await filesystem_service.get_stats()
        assert 'files_read' in stats
        assert 'files_written' in stats
        assert 'indexed_files' in stats
        assert stats['root_path'] == temp_dir

    @pytest.mark.asyncio
    async def test_file_type_classification(self, filesystem_service, sample_files):
        """Test file type classification"""
        # Test text file
        file_info = await filesystem_service.get_file_info(sample_files['test.txt'])
        assert file_info.type == FileType.TEXT
        
        # Test Python code file
        file_info = await filesystem_service.get_file_info(sample_files['script.py'])
        assert file_info.type == FileType.CODE
        
        # Test JSON file
        file_info = await filesystem_service.get_file_info(sample_files['data.json'])
        assert file_info.type == FileType.TEXT
        
        # Test directory
        file_info = await filesystem_service.get_file_info(sample_files['subdir'])
        assert file_info.type == FileType.DIRECTORY
        assert file_info.is_directory is True

    @pytest.mark.asyncio
    async def test_get_file_info(self, filesystem_service, sample_files):
        """Test getting file information"""
        file_info = await filesystem_service.get_file_info(sample_files['test.txt'])
        
        assert file_info is not None
        assert file_info.path == sample_files['test.txt']
        assert file_info.name == 'test.txt'
        assert file_info.size > 0
        assert file_info.type == FileType.TEXT
        assert file_info.extension == '.txt'
        assert file_info.is_directory is False
        assert file_info.is_hidden is False
        assert FilePermission.READ in file_info.permissions
        assert file_info.content_hash != ""
        
        # Test non-existent file
        file_info = await filesystem_service.get_file_info('/non/existent/file.txt')
        assert file_info is None

    @pytest.mark.asyncio
    async def test_read_file(self, filesystem_service, sample_files):
        """Test reading file content"""
        content = await filesystem_service.read_file(sample_files['test.txt'])
        assert content is not None
        assert "Hello World" in content
        assert "test file" in content
        assert "multiple lines" in content
        
        # Check statistics
        stats = await filesystem_service.get_stats()
        assert stats['files_read'] >= 1
        assert stats['total_bytes_read'] > 0
        
        # Test reading same file again (should use cache)
        content2 = await filesystem_service.read_file(sample_files['test.txt'])
        assert content2 == content
        
        # Test non-existent file
        content = await filesystem_service.read_file('/non/existent/file.txt')
        assert content is None

    @pytest.mark.asyncio
    async def test_write_file(self, filesystem_service, temp_dir):
        """Test writing file content"""
        test_file = os.path.join(temp_dir, 'new_file.txt')
        test_content = "This is new content\nWith multiple lines\nFor testing"
        
        # Write new file
        success = await filesystem_service.write_file(test_file, test_content)
        assert success is True
        
        # Verify file was created
        assert os.path.exists(test_file)
        
        # Read back content
        content = await filesystem_service.read_file(test_file)
        assert content == test_content
        
        # Check statistics
        stats = await filesystem_service.get_stats()
        assert stats['files_created'] >= 1
        assert stats['total_bytes_written'] > 0
        
        # Test overwriting existing file
        new_content = "Updated content"
        success = await filesystem_service.write_file(test_file, new_content)
        assert success is True
        
        content = await filesystem_service.read_file(test_file)
        assert content == new_content

    @pytest.mark.asyncio
    async def test_write_file_with_directories(self, filesystem_service, temp_dir):
        """Test writing file with automatic directory creation"""
        test_file = os.path.join(temp_dir, 'new_dir', 'subdir', 'file.txt')
        test_content = "Content in nested directory"
        
        success = await filesystem_service.write_file(test_file, test_content)
        assert success is True
        
        # Verify directory structure was created
        assert os.path.exists(os.path.dirname(test_file))
        assert os.path.exists(test_file)
        
        content = await filesystem_service.read_file(test_file)
        assert content == test_content

    @pytest.mark.asyncio
    async def test_delete_file(self, filesystem_service, sample_files):
        """Test deleting files"""
        # Delete regular file
        success = await filesystem_service.delete_file(sample_files['test.txt'])
        assert success is True
        assert not os.path.exists(sample_files['test.txt'])
        
        # Check statistics
        stats = await filesystem_service.get_stats()
        assert stats['files_deleted'] >= 1
        
        # Delete directory
        success = await filesystem_service.delete_file(sample_files['subdir'])
        assert success is True
        assert not os.path.exists(sample_files['subdir'])
        
        # Try to delete non-existent file
        success = await filesystem_service.delete_file('/non/existent/file.txt')
        assert success is False

    @pytest.mark.asyncio
    async def test_move_file(self, filesystem_service, sample_files, temp_dir):
        """Test moving/renaming files"""
        src_path = sample_files['test.txt']
        dest_path = os.path.join(temp_dir, 'moved_file.txt')
        
        # Read original content
        original_content = await filesystem_service.read_file(src_path)
        
        # Move file
        success = await filesystem_service.move_file(src_path, dest_path)
        assert success is True
        
        # Verify move
        assert not os.path.exists(src_path)
        assert os.path.exists(dest_path)
        
        # Verify content is preserved
        moved_content = await filesystem_service.read_file(dest_path)
        assert moved_content == original_content
        
        # Check statistics
        stats = await filesystem_service.get_stats()
        assert stats['files_moved'] >= 1
        
        # Try to move non-existent file
        success = await filesystem_service.move_file('/non/existent/file.txt', dest_path)
        assert success is False

    @pytest.mark.asyncio
    async def test_copy_file(self, filesystem_service, sample_files, temp_dir):
        """Test copying files"""
        src_path = sample_files['test.txt']
        dest_path = os.path.join(temp_dir, 'copied_file.txt')
        
        # Read original content
        original_content = await filesystem_service.read_file(src_path)
        
        # Copy file
        success = await filesystem_service.copy_file(src_path, dest_path)
        assert success is True
        
        # Verify copy
        assert os.path.exists(src_path)  # Original still exists
        assert os.path.exists(dest_path)
        
        # Verify content is preserved
        copied_content = await filesystem_service.read_file(dest_path)
        assert copied_content == original_content
        
        # Check statistics
        stats = await filesystem_service.get_stats()
        assert stats['files_copied'] >= 1
        
        # Try to copy non-existent file
        success = await filesystem_service.copy_file('/non/existent/file.txt', dest_path)
        assert success is False

    @pytest.mark.asyncio
    async def test_list_directory(self, filesystem_service, sample_files, temp_dir):
        """Test listing directory contents"""
        # List root directory
        files = await filesystem_service.list_directory(temp_dir)
        
        # Check that we have the expected files
        file_names = [f.name for f in files]
        assert 'test.txt' in file_names
        assert 'script.py' in file_names
        assert 'data.json' in file_names
        assert 'subdir' in file_names
        
        # Check that hidden files are not included by default
        assert '.hidden' not in file_names
        
        # Test including hidden files
        files_with_hidden = await filesystem_service.list_directory(temp_dir, include_hidden=True)
        hidden_names = [f.name for f in files_with_hidden]
        assert '.hidden' in hidden_names
        
        # Test recursive listing
        files_recursive = await filesystem_service.list_directory(temp_dir, recursive=True)
        recursive_names = [f.name for f in files_recursive]
        assert 'README.md' in recursive_names  # From subdirectory
        
        # Test non-existent directory
        files = await filesystem_service.list_directory('/non/existent/dir')
        assert files == []

    @pytest.mark.asyncio
    async def test_search_files_by_name(self, filesystem_service, sample_files):
        """Test searching files by name"""
        # Search for files containing 'test'
        results = await filesystem_service.search_files('test', search_content=False)
        
        # Should find test.txt
        assert len(results) > 0
        result_paths = [r.file_info.path for r in results]
        assert sample_files['test.txt'] in result_paths
        
        # Check search result structure
        result = results[0]
        assert isinstance(result, SearchResult)
        assert result.score > 0
        assert len(result.matches) > 0
        
        # Search for specific extension
        results = await filesystem_service.search_files('.py', search_content=False)
        assert len(results) > 0
        result_paths = [r.file_info.path for r in results]
        assert sample_files['script.py'] in result_paths
        
        # Search for non-existent file
        results = await filesystem_service.search_files('nonexistent', search_content=False)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_files_by_content(self, filesystem_service, sample_files):
        """Test searching files by content"""
        # Search for content in files
        results = await filesystem_service.search_files('Hello', search_content=True)
        
        # Should find files containing 'Hello'
        assert len(results) > 0
        
        # Check that we get content matches
        for result in results:
            if result.file_info.path == sample_files['test.txt']:
                assert any('Hello World' in match for match in result.matches)
                break
        else:
            assert False, "Expected to find test.txt in results"
        
        # Search for Python-specific content
        results = await filesystem_service.search_files('python', search_content=True)
        assert len(results) > 0
        
        # Check statistics
        stats = await filesystem_service.get_stats()
        assert stats['searches_performed'] >= 1

    @pytest.mark.asyncio
    async def test_search_with_file_types(self, filesystem_service, sample_files):
        """Test searching with file type filters"""
        # Search only code files
        results = await filesystem_service.search_files('print', search_content=True, 
                                                        file_types=[FileType.CODE])
        
        # Should find Python file
        assert len(results) > 0
        for result in results:
            assert result.file_info.type == FileType.CODE
        
        # Search only text files
        results = await filesystem_service.search_files('test', search_content=True, 
                                                        file_types=[FileType.TEXT])
        
        # Should find text files but not code files
        assert len(results) > 0
        for result in results:
            assert result.file_info.type == FileType.TEXT

    @pytest.mark.asyncio
    async def test_file_watching_events(self, filesystem_service, temp_dir):
        """Test file watching and event publishing"""
        # Mock message broker to capture events
        events_captured = []
        
        async def capture_event(message):
            events_captured.append((message.topic, message.payload))
        
        # Subscribe to file system events
        await filesystem_service.message_broker.subscribe('fs.*', capture_event)
        
        # Create a new file
        test_file = os.path.join(temp_dir, 'watched_file.txt')
        success = await filesystem_service.write_file(test_file, "Test content")
        assert success is True
        
        # Wait for events to be processed
        await asyncio.sleep(0.1)
        
        # Check that file written event was published
        write_events = [
            (topic, payload) for topic, payload in events_captured
            if topic == 'fs.file_written'
        ]
        assert len(write_events) > 0
        
        # Modify the file
        success = await filesystem_service.write_file(test_file, "Updated content")
        assert success is True
        
        # Wait for events
        await asyncio.sleep(0.1)
        
        # Check for modification events
        modify_events = [
            (topic, payload) for topic, payload in events_captured
            if topic == 'fs.file_written'
        ]
        assert len(modify_events) >= 2  # Initial write + update

    @pytest.mark.asyncio
    async def test_file_indexing(self, filesystem_service, sample_files):
        """Test file indexing and search index"""
        # Check that files are indexed
        stats = await filesystem_service.get_stats()
        assert stats['indexed_files'] > 0
        assert stats['search_index_size'] > 0
        
        # Check that text files are in the index
        assert sample_files['test.txt'] in filesystem_service.file_index
        assert sample_files['script.py'] in filesystem_service.file_index
        
        # Check search index contains words from files
        assert len(filesystem_service.search_index) > 0
        
        # Test that new files get indexed
        new_file = os.path.join(os.path.dirname(sample_files['test.txt']), 'new_indexed.txt')
        await filesystem_service.write_file(new_file, "Indexable content for testing")
        
        # File should be added to index
        assert new_file in filesystem_service.file_index

    @pytest.mark.asyncio
    async def test_content_caching(self, filesystem_service, sample_files):
        """Deprecated: caching removed. Verify read consistency instead."""
        content1 = await filesystem_service.read_file(sample_files['test.txt'])
        assert content1 is not None
        content2 = await filesystem_service.read_file(sample_files['test.txt'])
        assert content2 == content1

    @pytest.mark.asyncio
    async def test_path_validation(self, filesystem_service, temp_dir):
        """Test path validation for security"""
        # Valid path within root
        valid_path = os.path.join(temp_dir, 'test.txt')
        assert await filesystem_service.validate_path(valid_path) is True
        
        # Invalid path outside root
        invalid_path = '/etc/passwd'
        assert await filesystem_service.validate_path(invalid_path) is False
        
        # Path traversal attempt
        traversal_path = os.path.join(temp_dir, '../../../etc/passwd')
        assert await filesystem_service.validate_path(traversal_path) is False

    @pytest.mark.asyncio
    async def test_large_file_handling(self, filesystem_service, temp_dir):
        """Test handling of large files"""
        # Create a file larger than max_file_size
        large_file = os.path.join(temp_dir, 'large_file.txt')
        large_content = "A" * (filesystem_service.max_file_size + 1000)
        
        # Write should succeed
        success = await filesystem_service.write_file(large_file, large_content)
        assert success is True
        
        # Read should return None (file too large)
        content = await filesystem_service.read_file(large_file)
        assert content is None

    @pytest.mark.asyncio
    async def test_permission_handling(self, filesystem_service, sample_files):
        """Test file permission detection"""
        file_info = await filesystem_service.get_file_info(sample_files['test.txt'])
        
        # Should have read permission
        assert FilePermission.READ in file_info.permissions
        
        # Check that permissions are properly detected
        assert len(file_info.permissions) > 0
        assert file_info.owner != ""

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, filesystem_service, temp_dir):
        """Test concurrent file operations"""
        async def write_file(i):
            file_path = os.path.join(temp_dir, f'concurrent_{i}.txt')
            content = f"Content for file {i}"
            return await filesystem_service.write_file(file_path, content)
        
        async def read_file(i):
            file_path = os.path.join(temp_dir, f'concurrent_{i}.txt')
            return await filesystem_service.read_file(file_path)
        
        # Write files concurrently
        write_tasks = [write_file(i) for i in range(10)]
        write_results = await asyncio.gather(*write_tasks)
        
        # All writes should succeed
        assert all(write_results)
        
        # Read files concurrently
        read_tasks = [read_file(i) for i in range(10)]
        read_results = await asyncio.gather(*read_tasks)
        
        # All reads should succeed
        assert all(read_results)
        
        # Verify content
        for i, content in enumerate(read_results):
            assert content == f"Content for file {i}"

    @pytest.mark.asyncio
    async def test_error_handling(self, filesystem_service):
        """Test error handling for various scenarios"""
        # Test reading non-existent file
        content = await filesystem_service.read_file('/non/existent/file.txt')
        assert content is None
        
        # Test writing to invalid path
        success = await filesystem_service.write_file('/invalid/path/file.txt', "content", create_dirs=False)
        assert success is False
        
        # Test deleting non-existent file
        success = await filesystem_service.delete_file('/non/existent/file.txt')
        assert success is False
        
        # Test moving non-existent file
        success = await filesystem_service.move_file('/non/existent/src.txt', '/tmp/dest.txt')
        assert success is False
        
        # Test copying non-existent file
        success = await filesystem_service.copy_file('/non/existent/src.txt', '/tmp/dest.txt')
        assert success is False

    @pytest.mark.asyncio
    async def test_file_info_serialization(self, filesystem_service, sample_files):
        """Test FileInfo serialization and deserialization"""
        file_info = await filesystem_service.get_file_info(sample_files['test.txt'])
        
        # Test to_dict
        file_dict = file_info.to_dict()
        assert isinstance(file_dict, dict)
        assert file_dict['path'] == sample_files['test.txt']
        assert file_dict['name'] == 'test.txt'
        assert file_dict['type'] == 'text'
        
        # Test from_dict
        recreated_file_info = FileInfo.from_dict(file_dict)
        assert recreated_file_info.path == file_info.path
        assert recreated_file_info.name == file_info.name
        assert recreated_file_info.type == file_info.type

    @pytest.mark.asyncio
    async def test_search_result_serialization(self, filesystem_service, sample_files):
        """Test SearchResult serialization"""
        results = await filesystem_service.search_files('test', search_content=True)
        
        if results:
            result = results[0]
            result_dict = result.to_dict()
            
            assert isinstance(result_dict, dict)
            assert 'file_info' in result_dict
            assert 'matches' in result_dict
            assert 'score' in result_dict
            assert 'context' in result_dict

    @pytest.mark.asyncio
    async def test_statistics_accuracy(self, filesystem_service, temp_dir):
        """Test that statistics are accurately tracked (without cache metrics)"""
        # Get initial stats
        initial_stats = await filesystem_service.get_stats()
        
        # Perform operations
        test_file = os.path.join(temp_dir, 'stats_test.txt')
        await filesystem_service.write_file(test_file, "Test content")
        
        await filesystem_service.read_file(test_file)
        await filesystem_service.search_files('test')
        await filesystem_service.delete_file(test_file)
        
        # Get final stats
        final_stats = await filesystem_service.get_stats()
        
        assert final_stats['files_written'] >= initial_stats['files_written']
        assert final_stats['files_read'] >= initial_stats['files_read']
        assert final_stats['files_deleted'] >= initial_stats['files_deleted']
        assert 'cache_hits' not in final_stats
        assert 'cache_misses' not in final_stats

    @pytest.mark.asyncio
    async def test_hidden_file_handling(self, filesystem_service, sample_files):
        """Test handling of hidden files"""
        # Hidden file should be detected
        file_info = await filesystem_service.get_file_info(sample_files['hidden'])
        assert file_info.is_hidden is True
        
        # Hidden files should not be included in normal directory listings
        files = await filesystem_service.list_directory(os.path.dirname(sample_files['hidden']))
        hidden_files = [f for f in files if f.is_hidden]
        assert len(hidden_files) == 0
        
        # Hidden files should be included when requested
        files_with_hidden = await filesystem_service.list_directory(
            os.path.dirname(sample_files['hidden']), include_hidden=True
        )
        hidden_files = [f for f in files_with_hidden if f.is_hidden]
        assert len(hidden_files) > 0

    @pytest.mark.asyncio
    async def test_mime_type_detection(self, filesystem_service, sample_files):
        """Test MIME type detection"""
        # Text file
        file_info = await filesystem_service.get_file_info(sample_files['test.txt'])
        assert file_info.mime_type.startswith('text/')
        
        # Python file
        file_info = await filesystem_service.get_file_info(sample_files['script.py'])
        assert file_info.mime_type.startswith('text/') or 'python' in file_info.mime_type
        
        # JSON file
        file_info = await filesystem_service.get_file_info(sample_files['data.json'])
        assert 'json' in file_info.mime_type or file_info.mime_type.startswith('text/')

    @pytest.mark.asyncio
    async def test_create_directory(self, filesystem_service, temp_dir):
        """Test basic directory creation"""
        test_dir = os.path.join(temp_dir, 'new_directory')
        
        # Directory should not exist initially
        assert not os.path.exists(test_dir)
        
        # Create directory
        success = await filesystem_service.create_directory(test_dir)
        
        # Verify success
        assert success is True
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)
        
        # Verify file info
        file_info = await filesystem_service.get_file_info(test_dir)
        assert file_info is not None
        assert file_info.is_directory is True
        assert file_info.type == FileType.DIRECTORY

    @pytest.mark.asyncio
    async def test_create_nested_directory(self, filesystem_service, temp_dir):
        """Test nested directory creation with parents"""
        test_dir = os.path.join(temp_dir, 'parent', 'child', 'grandchild')
        
        # Directory should not exist initially
        assert not os.path.exists(test_dir)
        assert not os.path.exists(os.path.join(temp_dir, 'parent'))
        
        # Create nested directory with parents
        success = await filesystem_service.create_directory(test_dir, parents=True)
        
        # Verify success
        assert success is True
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)
        
        # Verify parent directories were created
        assert os.path.exists(os.path.join(temp_dir, 'parent'))
        assert os.path.exists(os.path.join(temp_dir, 'parent', 'child'))

    @pytest.mark.asyncio
    async def test_create_nested_directory_without_parents(self, filesystem_service, temp_dir):
        """Test nested directory creation without parents should fail"""
        test_dir = os.path.join(temp_dir, 'nonexistent', 'child')
        
        # Directory should not exist initially
        assert not os.path.exists(test_dir)
        assert not os.path.exists(os.path.join(temp_dir, 'nonexistent'))
        
        # Create nested directory without parents should fail
        success = await filesystem_service.create_directory(test_dir, parents=False)
        
        # Verify failure
        assert success is False
        assert not os.path.exists(test_dir)

    @pytest.mark.asyncio
    async def test_create_existing_directory(self, filesystem_service, temp_dir):
        """Test creating directory that already exists"""
        test_dir = os.path.join(temp_dir, 'existing_dir')
        
        # Create directory first
        os.makedirs(test_dir)
        assert os.path.exists(test_dir)
        
        # Try to create the same directory again
        success = await filesystem_service.create_directory(test_dir)
        
        # Should succeed (idempotent operation)
        assert success is True
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)

    @pytest.mark.asyncio
    async def test_create_directory_where_file_exists(self, filesystem_service, temp_dir):
        """Test creating directory where file already exists"""
        test_path = os.path.join(temp_dir, 'conflict_test')
        
        # Create a file first
        with open(test_path, 'w') as f:
            f.write('existing file')
        
        assert os.path.exists(test_path)
        assert os.path.isfile(test_path)
        
        # Try to create directory with same name
        success = await filesystem_service.create_directory(test_path)
        
        # Should fail
        assert success is False
        
        # File should still exist and be a file
        assert os.path.exists(test_path)
        assert os.path.isfile(test_path)

    @pytest.mark.asyncio
    async def test_create_directory_with_special_characters(self, filesystem_service, temp_dir):
        """Test creating directory with special characters in name"""
        special_names = [
            'directory with spaces',
            'directory-with-hyphens',
            'directory_with_underscores',
            'directory.with.dots'
        ]
        
        for dir_name in special_names:
            test_dir = os.path.join(temp_dir, dir_name)
            
            # Create directory
            success = await filesystem_service.create_directory(test_dir)
            
            # Verify success
            assert success is True, f"Failed to create directory: {dir_name}"
            assert os.path.exists(test_dir)
            assert os.path.isdir(test_dir)

    @pytest.mark.asyncio
    async def test_create_directory_event_publishing(self, filesystem_service, temp_dir):
        """Test that directory creation publishes events"""
        test_dir = os.path.join(temp_dir, 'event_test_dir')
        
        # Mock the message broker to capture events
        original_publish = filesystem_service.message_broker.publish
        published_events = []
        
        async def mock_publish(event_type, data):
            published_events.append((event_type, data))
            return await original_publish(event_type, data)
        
        filesystem_service.message_broker.publish = mock_publish
        
        # Create directory
        success = await filesystem_service.create_directory(test_dir)
        
        # Verify success and event publishing
        assert success is True
        assert os.path.exists(test_dir)
        
        # Check that the correct event was published
        directory_created_events = [event for event in published_events if event[0] == 'fs.directory_created']
        assert len(directory_created_events) == 1
        
        event_type, event_data = directory_created_events[0]
        assert event_data['dir_path'] == os.path.abspath(test_dir)
        assert event_data['parents'] is True
        assert 'timestamp' in event_data
        
        # Restore original publish method
        filesystem_service.message_broker.publish = original_publish

    @pytest.mark.asyncio
    async def test_create_directory_statistics_update(self, filesystem_service, temp_dir):
        """Test that directory creation updates statistics"""
        test_dir = os.path.join(temp_dir, 'stats_test_dir')
        
        # Get initial stats
        initial_stats = await filesystem_service.get_stats()
        initial_files_created = initial_stats['files_created']
        
        # Create directory
        success = await filesystem_service.create_directory(test_dir)
        
        # Verify stats were updated
        assert success is True
        final_stats = await filesystem_service.get_stats()
        assert final_stats['files_created'] == initial_files_created + 1

    @pytest.mark.asyncio
    async def test_create_directory_permissions(self, filesystem_service, temp_dir):
        """Test directory creation with proper permissions"""
        test_dir = os.path.join(temp_dir, 'permissions_test')
        
        # Create directory
        success = await filesystem_service.create_directory(test_dir)
        assert success is True
        
        # Check permissions
        file_info = await filesystem_service.get_file_info(test_dir)
        assert file_info is not None
        
        # Should have read and write permissions at minimum
        permission_values = [p.value for p in file_info.permissions]
        assert 'read' in permission_values
        assert 'write' in permission_values


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
