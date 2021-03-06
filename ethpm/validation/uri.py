import hashlib
from typing import (
    List,
)
from urllib import (
    parse,
)

from eth_utils import (
    is_checksum_address,
    to_bytes,
    to_int,
    to_text,
)

from ethpm._utils.chains import (
    is_supported_chain_id,
)
from ethpm._utils.ipfs import (
    is_ipfs_uri,
)
from ethpm._utils.registry import (
    is_ens_domain,
)
from ethpm.constants import (
    REGISTRY_URI_SCHEME,
)
from ethpm.exceptions import (
    EthPMValidationError,
)
from ethpm.validation.package import (
    validate_package_name,
)
from web3 import Web3


def validate_ipfs_uri(uri: str) -> None:
    """
    Raise an exception if the provided URI is not a valid IPFS URI.
    """
    if not is_ipfs_uri(uri):
        raise EthPMValidationError(f"URI: {uri} is not a valid IPFS URI.")


def validate_registry_uri(uri: str) -> None:
    """
    Raise an exception if the URI does not conform to the registry URI scheme.
    """
    parsed = parse.urlparse(uri)
    scheme, authority, pkg_path, version = (
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.query,
    )
    validate_registry_uri_scheme(scheme)
    validate_registry_uri_authority(authority)
    pkg_name = pkg_path.strip("/")
    if pkg_name:
        validate_package_name(pkg_name)
    if not pkg_name and version:
        raise EthPMValidationError("Registry URIs cannot provide a version without a package name.")
    if version:
        validate_registry_uri_version(version)


def validate_registry_uri_authority(auth: str) -> None:
    """
    Raise an exception if the authority is not a valid ENS domain
    or a valid checksummed contract address.
    """
    try:
        address, chain_id = auth.split(':')
    except ValueError:
        raise EthPMValidationError(
            f"{auth} is not a valid registry URI authority. "
            "Please try again with a valid registry URI."
        )

    if is_ens_domain(address) is False and not is_checksum_address(address):
        raise EthPMValidationError(
            f"{address} is not a valid registry address. "
            "Please try again with a valid registry URI."
        )

    if not is_supported_chain_id(to_int(text=chain_id)):
        raise EthPMValidationError(
            f"Chain ID: {chain_id} is not supported. Supported chain ids include: "
            "1 (mainnet), 3 (ropsten), 4 (rinkeby), 5 (goerli) and 42 (kovan). "
            "Please try again with a valid registry URI."
        )


def validate_registry_uri_scheme(scheme: str) -> None:
    """
    Raise an exception if the scheme is not the valid registry URI scheme ('ercXXX').
    """
    if scheme != REGISTRY_URI_SCHEME:
        raise EthPMValidationError(f"{scheme} is not a valid registry URI scheme.")


def validate_registry_uri_version(query: str) -> None:
    """
    Raise an exception if the version param is malformed.
    """
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    if "version" not in query_dict:
        raise EthPMValidationError(f"{query} is not a correctly formatted version param.")


def validate_single_matching_uri(all_blockchain_uris: List[str], w3: Web3) -> str:
    """
    Return a single block URI after validating that it is the *only* URI in
    all_blockchain_uris that matches the w3 instance.
    """
    from ethpm.uri import check_if_chain_matches_chain_uri

    matching_uris = [
        uri for uri in all_blockchain_uris if check_if_chain_matches_chain_uri(w3, uri)
    ]

    if not matching_uris:
        raise EthPMValidationError("Package has no matching URIs on chain.")
    elif len(matching_uris) != 1:
        raise EthPMValidationError(
            f"Package has too many ({len(matching_uris)}) matching URIs: {matching_uris}."
        )
    return matching_uris[0]


def validate_blob_uri_contents(contents: bytes, blob_uri: str) -> None:
    """
    Raises an exception if the sha1 hash of the contents does not match the hash found in te
    blob_uri. Formula for how git calculates the hash found here:
    http://alblue.bandlem.com/2011/08/git-tip-of-week-objects.html
    """
    blob_path = parse.urlparse(blob_uri).path
    blob_hash = blob_path.split("/")[-1]
    contents_str = to_text(contents)
    content_length = len(contents_str)
    hashable_contents = "blob " + str(content_length) + "\0" + contents_str
    hash_object = hashlib.sha1(to_bytes(text=hashable_contents))
    if hash_object.hexdigest() != blob_hash:
        raise EthPMValidationError(
            f"Hash of contents fetched from {blob_uri} do not match its hash: {blob_hash}."
        )
